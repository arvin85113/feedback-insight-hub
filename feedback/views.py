from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Count
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


class DashboardBaseMixin(ManagerRequiredMixin):
    dashboard_nav = [
        ("feedback:dashboard", "總覽儀表板", "grid"),
        ("feedback:survey-manager", "問卷管理", "clipboard"),
        ("feedback:stats-overview", "統計分析", "chart"),
        ("feedback:text-analysis", "文字分析", "message"),
        ("feedback:improvement-list", "改進追蹤", "wrench"),
        ("feedback:notice-center", "通告管理", "send"),
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
        context["surveys"] = Survey.objects.filter(is_active=True)
        return context


class DashboardView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/dashboard.html"
    active_section = "feedback:dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surveys = Survey.objects.prefetch_related("questions", "keyword_categories").all()
        submissions = FeedbackSubmission.objects.select_related("survey")
        improvements = ImprovementUpdate.objects.all()
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

        context.update(self.get_dashboard_base_context())
        context.update(
            {
                "metrics": [
                    {"label": "問卷總數", "value": total_surveys, "hint": f"{surveys.filter(is_active=True).count()} 份進行中", "accent": "blue"},
                    {"label": "回覆總數", "value": total_submissions, "hint": "所有問卷", "accent": "violet"},
                    {"label": "改進項目", "value": total_improvements, "hint": f"{improvements.filter(emailed_at__isnull=False).count()} 項已通知", "accent": "green"},
                    {"label": "平均回覆數", "value": avg_responses, "hint": "每份問卷", "accent": "amber"},
                ],
                "daily_counts": daily_counts,
                "recent_surveys": surveys[:5],
            }
        )
        return context


class SurveyManagerView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/survey_manager.html"
    active_section = "feedback:survey-manager"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surveys = Survey.objects.prefetch_related("questions").all()
        context.update(self.get_dashboard_base_context())
        context["surveys"] = surveys
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
        messages.success(self.request, "新問卷已建立，接著加入題目。")
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
            {"key": "questions", "label": "問題"},
            {"key": "responses", "label": "回覆"},
            {"key": "settings", "label": "設定"},
        ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action")

        if action == "delete-question":
            question = get_object_or_404(Question, id=request.POST.get("question_id"), survey=self.object)
            question.delete()
            messages.success(request, "題目已刪除。")
            return redirect("feedback:survey-builder", slug=self.object.slug)

        question_form = QuestionCreateForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.survey = self.object
            question.save()
            messages.success(request, "題目已加入表單。")
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
            messages.warning(request, "此問卷需要登入後填寫。")
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quick_form"] = QuickAccessForm(prefix="meta")
        context["form"] = SurveyFormBuilder(survey=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        quick_form = QuickAccessForm(request.POST, prefix="meta")
        form = SurveyFormBuilder(request.POST, survey=self.object)
        if form.is_valid() and quick_form.is_valid():
            submission = FeedbackSubmission.objects.create(
                survey=self.object,
                user=request.user if request.user.is_authenticated else None,
                respondent_name=quick_form.cleaned_data["respondent_name"],
                respondent_email=quick_form.cleaned_data["respondent_email"],
                consent_follow_up=quick_form.cleaned_data["consent_follow_up"],
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
                    subject=f"感謝您填寫 {self.object.title}",
                    message="您的回饋已收到，我們將用於後續產品與服務改善。",
                    from_email=None,
                    recipient_list=[submission.respondent_email],
                    fail_silently=True,
                )
            return HttpResponseRedirect(reverse("feedback:survey-success", args=[self.object.slug]))

        context = self.get_context_data(object=self.object)
        context["form"] = form
        context["quick_form"] = quick_form
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
        recipients = self.survey.submissions.filter(consent_follow_up=True).exclude(respondent_email="")
        if form.instance.related_category:
            recipients = recipients.filter(
                answers__question__survey=self.survey,
                answers__value__icontains=form.instance.related_category,
            ).distinct()

        for submission in recipients:
            ImprovementDispatch.objects.get_or_create(
                improvement=form.instance,
                submission=submission,
                defaults={"personalized_note": f"感謝您先前提出與「{form.instance.related_category or '整體服務'}」相關的意見。"},
            )
            send_mail(
                subject=f"{self.survey.title} 改進更新通知",
                message=f"{form.instance.summary}\n\n感謝您先前的回饋，這次更新與您的意見直接相關。",
                from_email=None,
                recipient_list=[submission.respondent_email],
                fail_silently=True,
            )
        messages.success(self.request, "改進追蹤通知已建立。")
        return response

    def get_success_url(self):
        return reverse_lazy("feedback:improvement-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
