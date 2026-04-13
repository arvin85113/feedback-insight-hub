from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, TemplateView

from .forms import (
    ImprovementUpdateForm,
    QuestionCreateForm,
    QuickAccessForm,
    SurveyCreateForm,
    SurveyFormBuilder,
)
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


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_manager


class CustomerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and not self.request.user.is_manager


class DashboardBaseMixin(ManagerRequiredMixin):
    dashboard_nav = [
        ("feedback:dashboard", "營運總覽", "grid"),
        ("feedback:survey-manager", "問卷管理", "clipboard"),
        ("feedback:stats-overview", "統計分析", "chart"),
        ("feedback:text-analysis", "文字分析", "message"),
        ("feedback:improvement-list", "改善追蹤", "wrench"),
        ("feedback:notice-center", "通知中心", "send"),
    ]

    active_section = ""

    def get_dashboard_base_context(self):
        return {
            "dashboard_nav": self.dashboard_nav,
            "active_section": self.active_section,
            "survey_list": Survey.objects.filter(is_active=True).order_by("title"),
        }


class HomeView(TemplateView):
    template_name = "feedback/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surveys = Survey.objects.filter(is_active=True).annotate(response_total=Count("submissions"))
        total_surveys = surveys.count()
        total_responses = FeedbackSubmission.objects.count()
        total_improvements = ImprovementUpdate.objects.count()
        context.update(
            {
                "surveys": surveys[:6],
                "active_survey_count": total_surveys,
                "response_count": total_responses,
                "improvement_count": total_improvements,
                "managed_clients": max(12, total_surveys * 3 or 12),
                "response_velocity": round(total_responses / total_surveys, 1) if total_surveys else 0,
                "featured_capabilities": [
                    {
                        "title": "Structured Feedback Pipeline",
                        "description": "從建立問卷、收集回覆、整理文字洞察到發布改善通知，讓團隊在同一條流程中管理整個回饋閉環。",
                    },
                    {
                        "title": "Customer Notification Control",
                        "description": "顧客可以選擇是否接收後續改善更新，平台也會保留每一筆填答與通知紀錄，降低溝通落差。",
                    },
                    {
                        "title": "Manager Command Console",
                        "description": "管理端集中呈現問卷、回覆、分類、改善與通知進度，方便用正式工作台方式追蹤營運狀態。",
                    },
                ],
                "homepage_steps": [
                    "建立正式對外問卷與填答入口。",
                    "收集顧客回饋並保留後續通知授權。",
                    "整理文字關鍵字與基礎統計摘要。",
                    "發布改善更新並追蹤通知是否送達。",
                ],
            }
        )
        return context


class CustomerHomeView(CustomerRequiredMixin, TemplateView):
    template_name = "feedback/customer_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submissions = (
            FeedbackSubmission.objects.filter(user=self.request.user)
            .select_related("survey")
            .prefetch_related("answers")
            .order_by("-submitted_at")
        )
        notices = (
            ImprovementDispatch.objects.filter(submission__user=self.request.user)
            .select_related("improvement", "submission", "submission__survey")
            .order_by("-sent_at")
        )
        submission_rows = []
        for submission in submissions[:8]:
            related_notice = notices.filter(submission=submission).first()
            submission_rows.append(
                {
                    "submission": submission,
                    "answer_count": submission.answers.count(),
                    "latest_notice": related_notice,
                }
            )

        context.update(
            {
                "submissions": submissions,
                "notices": notices[:10],
                "submission_rows": submission_rows,
                "submission_count": submissions.count(),
                "active_follow_up_count": submissions.filter(consent_follow_up=True).count(),
                "latest_submission": submissions.first(),
                "latest_notice": notices.first(),
                "subscribed_survey_count": submissions.values("survey").distinct().count(),
            }
        )
        return context


class CustomerNotificationsView(CustomerRequiredMixin, TemplateView):
    template_name = "feedback/customer_notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notices = (
            ImprovementDispatch.objects.filter(submission__user=self.request.user)
            .select_related("improvement", "submission", "submission__survey")
            .order_by("-sent_at")
        )
        context.update(
            {
                "notices": notices,
                "notification_opt_in": self.request.user.notification_opt_in,
                "notice_count": notices.count(),
                "latest_notice": notices.first(),
            }
        )
        return context


class DashboardView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/dashboard.html"
    active_section = "feedback:dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surveys = Survey.objects.prefetch_related("questions", "keyword_categories").all()
        submissions = FeedbackSubmission.objects.select_related("survey")
        improvements = ImprovementUpdate.objects.select_related("survey").all()
        last_week = timezone.now() - timedelta(days=6)

        daily_counts = []
        for index in range(7):
            target_day = (last_week + timedelta(days=index)).date()
            total = submissions.filter(submitted_at__date=target_day).count()
            daily_counts.append({"label": target_day.strftime("%m/%d"), "total": total})

        total_surveys = surveys.count()
        total_submissions = submissions.count()
        total_improvements = improvements.count()
        avg_responses = round(total_submissions / total_surveys, 1) if total_surveys else 0

        top_surveys = sorted(surveys, key=lambda survey: survey.submissions.count(), reverse=True)[:5]
        recent_responses = submissions.order_by("-submitted_at")[:6]
        latest_improvements = improvements[:5]

        context.update(self.get_dashboard_base_context())
        context.update(
            {
                "metrics": [
                    {
                        "label": "啟用中問卷",
                        "value": total_surveys,
                        "hint": f"{surveys.filter(is_active=True).count()} 份目前對外開放",
                        "accent": "blue",
                    },
                    {
                        "label": "累積回覆數",
                        "value": total_submissions,
                        "hint": "包含登入與免登入來源",
                        "accent": "violet",
                    },
                    {
                        "label": "改善更新數",
                        "value": total_improvements,
                        "hint": f"{improvements.filter(emailed_at__isnull=False).count()} 則已完成通知",
                        "accent": "green",
                    },
                    {
                        "label": "平均每份回覆",
                        "value": avg_responses,
                        "hint": "作為問卷活躍度的基礎觀察",
                        "accent": "amber",
                    },
                ],
                "daily_counts": daily_counts,
                "recent_surveys": surveys[:5],
                "top_surveys": top_surveys,
                "recent_responses": recent_responses,
                "latest_improvements": latest_improvements,
            }
        )
        return context


class SurveyManagerView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/survey_manager.html"
    active_section = "feedback:survey-manager"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["surveys"] = Survey.objects.prefetch_related("questions").all()
        return context


class SurveyCreateView(DashboardBaseMixin, CreateView):
    template_name = "feedback/survey_create.html"
    form_class = SurveyCreateForm
    active_section = "feedback:survey-manager"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        return context

    def form_valid(self, form):
        messages.success(self.request, "問卷已建立，接著可以新增題目並設定分享方式。")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("feedback:survey-builder", args=[self.object.slug])


class SurveyBuilderView(DashboardBaseMixin, DetailView):
    template_name = "feedback/survey_builder.html"
    context_object_name = "survey"
    model = Survey
    slug_field = "slug"
    slug_url_kwarg = "slug"
    active_section = "feedback:survey-manager"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["question_form"] = kwargs.get("question_form") or QuestionCreateForm(
            initial={"order": self.object.questions.count() + 1}
        )
        context["responses_count"] = self.object.submissions.count()
        context["builder_tabs"] = [
            {"key": "questions", "label": "題目編排"},
            {"key": "responses", "label": "回覆狀況"},
            {"key": "settings", "label": "入口設定"},
        ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action")

        if action == "delete-question":
            question = get_object_or_404(Question, id=request.POST.get("question_id"), survey=self.object)
            question.delete()
            messages.success(request, "題目已從問卷中移除。")
            return redirect("feedback:survey-builder", slug=self.object.slug)

        question_form = QuestionCreateForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.survey = self.object
            question.save()
            messages.success(request, "新題目已加入問卷。")
            return redirect("feedback:survey-builder", slug=self.object.slug)

        context = self.get_context_data(question_form=question_form, object=self.object)
        return self.render_to_response(context)


class StatsOverviewView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/stats_overview.html"
    active_section = "feedback:stats-overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_slug = self.request.GET.get("survey")
        survey = Survey.objects.filter(slug=selected_slug).first() if selected_slug else None
        context.update(self.get_dashboard_base_context())
        context["selected_survey"] = survey
        context["charts"] = chart_summary(survey) if survey else []
        context["question_analysis"] = (
            [
                {
                    "title": question.title,
                    "data_type": question.get_data_type_display(),
                    "analysis": recommend_analysis(question),
                }
                for question in survey.questions.all()
            ]
            if survey
            else []
        )
        return context


class TextAnalysisView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/text_analysis.html"
    active_section = "feedback:text-analysis"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_slug = self.request.GET.get("survey")
        survey = Survey.objects.filter(slug=selected_slug).first() if selected_slug else None
        context.update(self.get_dashboard_base_context())
        context["selected_survey"] = survey
        context["keywords"] = keyword_summary(survey) if survey else []
        context["text_questions"] = survey.questions.filter(data_type=Question.DataType.TEXT) if survey else []
        return context


class ImprovementListView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/improvement_list.html"
    active_section = "feedback:improvement-list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["improvements"] = ImprovementUpdate.objects.select_related("survey").all()
        return context


class NoticeCenterView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/notice_center.html"
    active_section = "feedback:notice-center"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["notices"] = ImprovementUpdate.objects.select_related("survey").all()
        return context


class SurveyDetailView(DetailView):
    template_name = "feedback/survey_detail.html"
    context_object_name = "survey"
    model = Survey
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.access_mode == Survey.AccessMode.LOGIN and not request.user.is_authenticated:
            messages.warning(request, "這份問卷需要先登入才能填寫。")
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = {}
        if self.request.user.is_authenticated:
            initial = {
                "respondent_name": self.request.user.get_full_name(),
                "respondent_email": self.request.user.email,
                "consent_follow_up": getattr(self.request.user, "notification_opt_in", False),
            }
        context["quick_form"] = kwargs.get("quick_form") or QuickAccessForm(prefix="meta", initial=initial)
        context["form"] = kwargs.get("form") or SurveyFormBuilder(survey=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        quick_form = QuickAccessForm(request.POST, prefix="meta")
        form = SurveyFormBuilder(request.POST, survey=self.object)
        if form.is_valid() and quick_form.is_valid():
            consent_follow_up = quick_form.cleaned_data["consent_follow_up"]
            if request.user.is_authenticated and not request.user.is_manager:
                request.user.notification_opt_in = consent_follow_up
                request.user.save(update_fields=["notification_opt_in"])

            submission = FeedbackSubmission.objects.create(
                survey=self.object,
                user=request.user if request.user.is_authenticated else None,
                respondent_name=quick_form.cleaned_data["respondent_name"],
                respondent_email=quick_form.cleaned_data["respondent_email"],
                consent_follow_up=consent_follow_up,
                source=Survey.AccessMode.LOGIN if request.user.is_authenticated else Survey.AccessMode.QUICK,
            )
            for question in self.object.questions.all():
                key = f"question_{question.id}"
                value = form.cleaned_data.get(key)
                if isinstance(value, list):
                    value = ", ".join(value)
                Answer.objects.create(submission=submission, question=question, value=value)

            if self.object.thank_you_email_enabled and submission.respondent_email:
                send_mail(
                    subject=f"感謝你填寫 {self.object.title}",
                    message="我們已收到你的回覆，後續若有改善更新，會依你的通知偏好提供後續資訊。",
                    from_email=None,
                    recipient_list=[submission.respondent_email],
                    fail_silently=True,
                )
            return HttpResponseRedirect(reverse("feedback:survey-success", args=[self.object.slug]))

        context = self.get_context_data(object=self.object, form=form, quick_form=quick_form)
        return self.render_to_response(context)


class QuickSurveyView(SurveyDetailView):
    template_name = "feedback/survey_quick.html"


class SurveySubmitSuccessView(TemplateView):
    template_name = "feedback/survey_success.html"


class ImprovementCreateView(ManagerRequiredMixin, CreateView):
    template_name = "feedback/improvement_form.html"
    form_class = ImprovementUpdateForm

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(Survey, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.survey = self.survey
        response = super().form_valid(form)
        recipients = (
            self.survey.submissions.select_related("user")
            .filter(Q(consent_follow_up=True) | Q(user__notification_opt_in=True))
            .exclude(respondent_email="")
        )
        if form.instance.related_category:
            recipients = recipients.filter(
                answers__question__survey=self.survey,
                answers__value__icontains=form.instance.related_category,
            ).distinct()

        sent_count = 0
        for submission in recipients:
            if submission.user and not submission.user.notification_opt_in:
                continue
            if not submission.consent_follow_up and not (submission.user and submission.user.notification_opt_in):
                continue

            dispatch, created = ImprovementDispatch.objects.get_or_create(
                improvement=form.instance,
                submission=submission,
                defaults={
                    "personalized_note": (
                        f"你會收到這則通知，是因為你曾對「{form.instance.related_category or self.survey.title}」"
                        "相關內容提供回饋，我們已根據意見展開改善。"
                    )
                },
            )
            if not created:
                continue

            send_mail(
                subject=f"{self.survey.title} 改善更新通知",
                message=f"{form.instance.title}\n\n{form.instance.summary}",
                from_email=None,
                recipient_list=[submission.respondent_email],
                fail_silently=True,
            )
            sent_count += 1

        if sent_count:
            form.instance.emailed_at = timezone.now()
            form.instance.save(update_fields=["emailed_at"])
        messages.success(self.request, "改善項目已建立，並完成通知派送。")
        return response

    def get_success_url(self):
        return reverse_lazy("feedback:improvement-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
