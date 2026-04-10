from django.urls import path

from .views import DashboardView, HomeView, ImprovementCreateView, QuickSurveyView, SurveyDetailView, SurveySubmitSuccessView

app_name = "feedback"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("survey/<slug:slug>/", SurveyDetailView.as_view(), name="survey-detail"),
    path("survey/<slug:slug>/quick/", QuickSurveyView.as_view(), name="survey-quick"),
    path("survey/<slug:slug>/success/", SurveySubmitSuccessView.as_view(), name="survey-success"),
    path("survey/<slug:slug>/improvement/new/", ImprovementCreateView.as_view(), name="improvement-create"),
]
