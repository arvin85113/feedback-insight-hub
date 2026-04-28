from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, TemplateView, View

from .forms import (
    ImprovementUpdateForm,
    QuestionCreateForm,
    QuickAccessForm,
    SurveyCreateForm,
    SurveyFormBuilder,
)
from .models import ImprovementDispatch, ImprovementUpdate, Question, Survey
from .service_client import service_client


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
        ("feedback:text-analysis", "文字洞察", "message"),
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
        context.update(service_client.get_home())
        context.update(
            {
                "featured_capabilities": [
                    {
                        "title": "Survey Operations",
                        "description": "統一管理問卷、題型與填答入口，讓前台首頁與後台配置維持同一套產品語言。",
                    },
                    {
                        "title": "Customer Follow-up",
                        "description": "顧客登入後可查看自己填過的問卷與改善通知，形成完整的回饋閉環。",
                    },
                    {
                        "title": "Insight Workspace",
                        "description": "管理端集中檢視量化統計、文字關鍵字與改善追蹤，維持正式 SaaS 工作流。",
                    },
                ],
                "homepage_steps": [
                    "建立正式問卷與填答模式",
                    "收集回覆並沉澱顧客原聲",
                    "從統計與文字分析提取線索",
                    "發布改善並回推通知給顧客",
                ],
            }
        )
        return context


class CustomerHomeView(CustomerRequiredMixin, TemplateView):
    template_name = "feedback/customer_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(service_client.get_customer_home(self.request.user))
        return context


class CustomerNotificationsView(CustomerRequiredMixin, TemplateView):
    template_name = "feedback/customer_notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(service_client.get_customer_notifications(self.request.user))
        context["notification_opt_in"] = self.request.user.notification_opt_in
        return context


class MarkNoticeReadView(CustomerRequiredMixin, View):
    def post(self, request, pk):
        dispatch = get_object_or_404(
            ImprovementDispatch,
            pk=pk,
            submission__user=request.user,
        )
        dispatch.is_read = True
        dispatch.save(update_fields=["is_read"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("feedback:customer-notifications")


class DashboardView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/dashboard.html"
    active_section = "feedback:dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context.update(service_client.get_dashboard())
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
        messages.success(self.request, "問卷已建立，接著可以進入題目編輯器完成配置。")
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
            {"key": "questions", "label": "題目設定"},
            {"key": "responses", "label": "回覆概況"},
            {"key": "settings", "label": "問卷設定"},
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
        payload = service_client.get_stats(selected_slug) if selected_slug else {"charts": [], "question_analysis": []}
        context["charts"] = payload["charts"]
        context["question_analysis"] = payload["question_analysis"]
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
        context["keywords"] = service_client.get_text_analysis(selected_slug)["keywords"] if selected_slug else []
        context["text_questions"] = survey.questions.filter(data_type=Question.DataType.TEXT) if survey else []
        return context


class ImprovementListView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/improvement_list.html"
    active_section = "feedback:improvement-list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        all_improvements = ImprovementUpdate.objects.select_related("survey").order_by("survey_id", "-created_at")
        improvements_by_survey = defaultdict(list)
        for imp in all_improvements:
            improvements_by_survey[imp.survey_id].append(imp)
        surveys = Survey.objects.order_by("title")
        context["survey_groups"] = [
            {
                "survey": survey,
                "improvements": improvements_by_survey[survey.id],
                "create_url": reverse("feedback:improvement-create", args=[survey.slug]),
            }
            for survey in surveys
        ]
        return context


class NoticeCenterView(DashboardBaseMixin, TemplateView):
    template_name = "feedback/notice_center.html"
    active_section = "feedback:notice-center"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["notices"] = (
            ImprovementUpdate.objects.select_related("survey")
            .annotate(dispatch_count=Count("dispatches"))
            .order_by("-created_at")
        )
        return context


class NoticeDetailView(DashboardBaseMixin, DetailView):
    template_name = "feedback/notice_detail.html"
    model = ImprovementUpdate
    context_object_name = "improvement"
    active_section = "feedback:notice-center"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_dashboard_base_context())
        context["dispatches"] = (
            self.object.dispatches
            .select_related("submission__user", "submission__survey")
            .order_by("-sent_at")
        )
        return context


class SurveyDetailView(DetailView):
    template_name = "feedback/survey_detail.html"
    context_object_name = "survey"
    model = Survey
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            messages.warning(request, "這份問卷需要先登入後才能填答。")
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

            submission_result = service_client.submit_survey(
                self.object,
                user=request.user if request.user.is_authenticated else None,
                respondent_name=quick_form.cleaned_data["respondent_name"],
                respondent_email=quick_form.cleaned_data["respondent_email"],
                consent_follow_up=consent_follow_up,
                source=Survey.AccessMode.LOGIN,
                answers={key: value for key, value in form.cleaned_data.items()},
            )

            if submission_result["thank_you_email_enabled"] and submission_result["respondent_email"]:
                send_mail(
                    subject=f"感謝填寫 {submission_result['survey_title']}",
                    message="我們已收到你的回覆。若後續有對應的改善通知，將依你的偏好主動提供最新進度。",
                    from_email=None,
                    recipient_list=[submission_result["respondent_email"]],
                    fail_silently=True,
                )
            return HttpResponseRedirect(reverse("feedback:survey-success", args=[self.object.slug]))

        context = self.get_context_data(object=self.object, form=form, quick_form=quick_form)
        return self.render_to_response(context)


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
                        f"你先前在 {form.instance.related_category or self.survey.title} 提供的回饋，"
                        "已被納入這次改善項目中，因此我們主動把最新進度同步給你。"
                    )
                },
            )
            if not created:
                continue

            send_mail(
                subject=f"{self.survey.title} 改善進度通知",
                message=f"{form.instance.title}\n\n{form.instance.summary}",
                from_email=None,
                recipient_list=[submission.respondent_email],
                fail_silently=True,
            )
            sent_count += 1

        if sent_count:
            form.instance.emailed_at = timezone.now()
            form.instance.save(update_fields=["emailed_at"])
        messages.success(self.request, f"改善通知已建立，並成功寄送給 {sent_count} 位填答者。")
        return response

    def get_success_url(self):
        return reverse_lazy("feedback:improvement-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
