from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, TemplateView

from .forms import ImprovementUpdateForm, QuickAccessForm, SurveyFormBuilder
from .models import (
    Answer,
    FeedbackSubmission,
    ImprovementDispatch,
    Survey,
    chart_summary,
    keyword_summary,
    recommend_analysis,
)


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_manager


class HomeView(TemplateView):
    template_name = "feedback/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["surveys"] = Survey.objects.filter(is_active=True)
        return context


class DashboardView(ManagerRequiredMixin, TemplateView):
    template_name = "feedback/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surveys = Survey.objects.prefetch_related("questions", "keyword_categories").all()
        summary = []
        for survey in surveys:
            questions = [
                {
                    "title": question.title,
                    "data_type": question.get_data_type_display(),
                    "analysis": recommend_analysis(question),
                }
                for question in survey.questions.all()
            ]
            summary.append(
                {
                    "survey": survey,
                    "submission_count": survey.submissions.count(),
                    "question_count": survey.questions.count(),
                    "keywords": keyword_summary(survey),
                    "charts": chart_summary(survey),
                    "questions": questions,
                }
            )
        context["summary"] = summary
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
        return reverse_lazy("feedback:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey"] = self.survey
        return context
