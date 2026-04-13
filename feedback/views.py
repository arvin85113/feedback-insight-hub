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
        ("feedback:dashboard", "Overview", "grid"),
        ("feedback:survey-manager", "Surveys", "clipboard"),
        ("feedback:stats-overview", "Analytics", "chart"),
        ("feedback:text-analysis", "Text Analysis", "message"),
        ("feedback:improvement-list", "Improvements", "wrench"),
        ("feedback:notice-center", "Announcements", "send"),
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
        context.update(
            {
                "surveys": surveys[:6],
                "active_survey_count": surveys.count(),
                "response_count": FeedbackSubmission.objects.count(),
                "improvement_count": ImprovementUpdate.objects.count(),
                "managed_clients": max(12, surveys.count() * 3 or 12),
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
        context.update(
            {
                "submissions": submissions,
                "notices": notices[:10],
                "submission_count": submissions.count(),
                "active_follow_up_count": submissions.filter(consent_follow_up=True).count(),
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
                    {
                        "label": "Active surveys",
                        "value": total_surveys,
                        "hint": f"{surveys.filter(is_active=True).count()} currently accepting responses",
                        "accent": "blue",
                    },
                    {
                        "label": "Total responses",
                        "value": total_submissions,
                        "hint": "Latest customer feedback across all forms",
                        "accent": "violet",
                    },
                    {
                        "label": "Improvement updates",
                        "value": total_improvements,
                        "hint": f"{improvements.filter(emailed_at__isnull=False).count()} already notified",
                        "accent": "green",
                    },
                    {
                        "label": "Average responses",
                        "value": avg_responses,
                        "hint": "Average responses per survey",
                        "accent": "amber",
                    },
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
        messages.success(self.request, "Survey created. You can now add questions and sharing options.")
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
            {"key": "questions", "label": "Questions"},
            {"key": "responses", "label": "Responses"},
            {"key": "settings", "label": "Settings"},
        ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action")

        if action == "delete-question":
            question = get_object_or_404(Question, id=request.POST.get("question_id"), survey=self.object)
            question.delete()
            messages.success(request, "Question removed from this survey.")
            return redirect("feedback:survey-builder", slug=self.object.slug)

        question_form = QuestionCreateForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.survey = self.object
            question.save()
            messages.success(request, "Question added to the survey.")
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
            messages.warning(request, "This survey requires sign-in before submission.")
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
                    subject=f"Thank you for your feedback on {self.object.title}",
                    message="We have received your response and will use it to improve the experience.",
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
                        f"You are receiving this update because you opted in to improvements for "
                        f"{form.instance.related_category or self.survey.title}."
                    )
                },
            )
            if not created:
                continue

            send_mail(
                subject=f"{self.survey.title} improvement update",
                message=f"{form.instance.title}\n\n{form.instance.summary}",
                from_email=None,
                recipient_list=[submission.respondent_email],
                fail_silently=True,
            )
            sent_count += 1

        form.instance.emailed_at = timezone.now() if sent_count else form.instance.emailed_at
        if sent_count:
            form.instance.save(update_fields=["emailed_at"])
        messages.success(self.request, "Improvement update created and dispatched.")
        return response

    def get_success_url(self):
        return reverse_lazy("feedback:improvement-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
