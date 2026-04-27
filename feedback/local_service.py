from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import (
    Answer,
    FeedbackSubmission,
    ImprovementDispatch,
    ImprovementUpdate,
    Question,
    Survey,
    chart_summary,
    keyword_summary,
    recommend_analysis,
)


ACCESS_MODE_LABELS = {
    Survey.AccessMode.LOGIN: "登入後填答",
}


def serialize_survey(survey, response_total=None):
    return {
        "id": survey.id,
        "title": survey.title,
        "slug": survey.slug,
        "description": survey.description,
        "access_mode": survey.access_mode,
        "access_mode_display": ACCESS_MODE_LABELS.get(survey.access_mode, survey.access_mode),
        "improvement_tracking_enabled": survey.improvement_tracking_enabled,
        "thank_you_email_enabled": survey.thank_you_email_enabled,
        "questions": {"count": survey.questions.count()},
        "submissions": {"count": response_total if response_total is not None else survey.submissions.count()},
    }


def serialize_submission(submission, answer_count=None):
    return {
        "id": submission.id,
        "submitted_at": submission.submitted_at.isoformat(),
        "consent_follow_up": submission.consent_follow_up,
        "respondent_email": submission.respondent_email,
        "display_name": submission.display_name,
        "survey": {
            "id": submission.survey.id,
            "title": submission.survey.title,
            "slug": submission.survey.slug,
        },
        "answers": {"count": answer_count if answer_count is not None else submission.answers.count()},
    }


def serialize_notice(notice):
    return {
        "id": notice.id,
        "sent_at": notice.sent_at.isoformat(),
        "personalized_note": notice.personalized_note,
        "submission": {
            "id": notice.submission.id,
            "survey": {
                "id": notice.submission.survey.id,
                "title": notice.submission.survey.title,
                "slug": notice.submission.survey.slug,
            },
        },
        "improvement": {
            "id": notice.improvement.id,
            "title": notice.improvement.title,
            "summary": notice.improvement.summary,
        },
    }


def get_home_payload():
    surveys = Survey.objects.filter(is_active=True).prefetch_related("questions", "submissions")
    total_surveys = surveys.count()
    total_responses = FeedbackSubmission.objects.count()
    total_improvements = ImprovementUpdate.objects.count()
    return {
        "surveys": [serialize_survey(survey, survey.submissions.count()) for survey in surveys[:6]],
        "active_survey_count": total_surveys,
        "response_count": total_responses,
        "improvement_count": total_improvements,
        "managed_clients": max(12, total_surveys * 3 or 12),
        "response_velocity": round(total_responses / total_surveys, 1) if total_surveys else 0,
    }


def get_customer_home_payload(user):
    submissions = list(
        FeedbackSubmission.objects.filter(user=user)
        .select_related("survey")
        .prefetch_related("answers")
        .order_by("-submitted_at")
    )
    notices = list(
        ImprovementDispatch.objects.filter(submission__user=user)
        .select_related("improvement", "submission", "submission__survey")
        .order_by("-sent_at")
    )
    notices_by_submission = {}
    for notice in notices:
        notices_by_submission.setdefault(notice.submission_id, notice)

    submission_rows = []
    for submission in submissions[:8]:
        related_notice = notices_by_submission.get(submission.id)
        answer_count = submission.answers.count()
        submission_rows.append(
            {
                "submission": serialize_submission(submission, answer_count),
                "answer_count": answer_count,
                "latest_notice": serialize_notice(related_notice) if related_notice else None,
            }
        )
    return {
        "submissions": [serialize_submission(s, s.answers.count()) for s in submissions],
        "notices": [serialize_notice(n) for n in notices[:10]],
        "submission_rows": submission_rows,
        "submission_count": len(submissions),
        "active_follow_up_count": sum(1 for s in submissions if s.consent_follow_up),
        "latest_submission": serialize_submission(submissions[0], submissions[0].answers.count()) if submissions else None,
        "latest_notice": serialize_notice(notices[0]) if notices else None,
        "subscribed_survey_count": len({s.survey_id for s in submissions}),
    }


def get_customer_notifications_payload(user):
    notices = (
        ImprovementDispatch.objects.filter(submission__user=user)
        .select_related("improvement", "submission", "submission__survey")
        .order_by("-sent_at")
    )
    return {
        "notices": [serialize_notice(notice) for notice in notices],
        "notice_count": notices.count(),
        "latest_notice": serialize_notice(notices.first()) if notices.exists() else None,
    }


def get_dashboard_payload():
    improvements = ImprovementUpdate.objects.select_related("survey").all()
    last_week = timezone.now() - timedelta(days=6)

    daily_qs = (
        FeedbackSubmission.objects.filter(submitted_at__gte=last_week)
        .annotate(day=TruncDate("submitted_at"))
        .values("day")
        .annotate(total=Count("id"))
    )
    counts_by_day = {row["day"]: row["total"] for row in daily_qs}
    daily_counts = [
        {
            "label": (last_week + timedelta(days=i)).date().strftime("%m/%d"),
            "total": counts_by_day.get((last_week + timedelta(days=i)).date(), 0),
        }
        for i in range(7)
    ]

    total_surveys = Survey.objects.count()
    total_submissions = FeedbackSubmission.objects.count()
    total_improvements = improvements.count()
    avg_responses = round(total_submissions / total_surveys, 1) if total_surveys else 0
    top_surveys = list(Survey.objects.annotate(sub_count=Count("submissions")).order_by("-sub_count")[:5])
    recent_responses = FeedbackSubmission.objects.select_related("survey", "user").order_by("-submitted_at")[:6]
    latest_improvements = improvements[:5]
    active_surveys = Survey.objects.filter(is_active=True).count()
    emailed_improvements = improvements.filter(emailed_at__isnull=False).count()

    insights = [
        {
            "title": "問卷活躍度",
            "body": f"目前共有 {active_surveys} 份啟用中的問卷，平均每份問卷 {avg_responses} 份回覆。",
            "tone": "neutral",
        },
        {
            "title": "顧客通知閉環",
            "body": f"已有 {emailed_improvements} 則改善項目完成通知寄送，可持續強化顧客信任。",
            "tone": "positive" if emailed_improvements else "neutral",
        },
        {
            "title": "優先關注目標",
            "body": f"{top_surveys[0].title if top_surveys else '目前尚無熱門問卷'} 是最適合先做深度分析與改善追蹤的入口。",
            "tone": "attention" if top_surveys else "neutral",
        },
    ]
    action_items = [
        {
            "title": "建立新問卷",
            "meta": "新增題組、整理題目流程與通知規則。",
            "url": "/dashboard/forms/new/",
            "url_label": "開始建立",
        },
        {
            "title": "查看統計總覽",
            "meta": "檢查連續變數、選項分布與可用分析方法。",
            "url": "/dashboard/stats/",
            "url_label": "前往分析",
        },
        {
            "title": "追蹤改善通知",
            "meta": "整理已建立的改善項目與通知派送情況。",
            "url": "/dashboard/notices/",
            "url_label": "查看通知",
        },
    ]

    return {
        "metrics": [
            {
                "label": "問卷總數",
                "value": total_surveys,
                "hint": f"{active_surveys} 份目前啟用",
                "accent": "blue",
            },
            {
                "label": "有效回覆",
                "value": total_submissions,
                "hint": "累積收到的顧客回應量",
                "accent": "violet",
            },
            {
                "label": "改善項目",
                "value": total_improvements,
                "hint": f"{emailed_improvements} 則已完成通知",
                "accent": "green",
            },
            {
                "label": "平均回覆量",
                "value": avg_responses,
                "hint": "每份問卷平均回覆數",
                "accent": "amber",
            },
        ],
        "daily_counts": daily_counts,
        "top_surveys": [serialize_survey(survey, survey.sub_count) for survey in top_surveys],
        "recent_responses": [serialize_submission(item) for item in recent_responses],
        "latest_improvements": [
            {
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "emailed_at": item.emailed_at.isoformat() if item.emailed_at else None,
                "survey": {"id": item.survey.id, "title": item.survey.title, "slug": item.survey.slug},
            }
            for item in latest_improvements
        ],
        "insights": insights,
        "action_items": action_items,
    }


def get_stats_payload(slug):
    survey = Survey.objects.filter(slug=slug).first() if slug else None
    if not survey:
        return {"charts": [], "question_analysis": []}
    return {
        "charts": chart_summary(survey),
        "question_analysis": [
            {
                "title": question.title,
                "data_type": question.get_data_type_display(),
                "analysis": recommend_analysis(question),
            }
            for question in survey.questions.all()
        ],
    }


def get_text_analysis_payload(slug):
    survey = Survey.objects.filter(slug=slug).first() if slug else None
    if not survey:
        return {"keywords": []}
    return {"keywords": keyword_summary(survey)}


def submit_survey_payload(survey, *, user, respondent_name, respondent_email, consent_follow_up, source, answers):
    submission = FeedbackSubmission.objects.create(
        survey=survey,
        user=user,
        respondent_name=respondent_name,
        respondent_email=respondent_email,
        consent_follow_up=consent_follow_up,
        source=source,
    )
    for question in survey.questions.all():
        key = f"question_{question.id}"
        value = answers.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            value = ", ".join(value)
        Answer.objects.create(submission=submission, question=question, value=value)
    return {
        "submission_id": submission.id,
        "thank_you_email_enabled": survey.thank_you_email_enabled,
        "respondent_email": submission.respondent_email,
        "survey_title": survey.title,
    }
