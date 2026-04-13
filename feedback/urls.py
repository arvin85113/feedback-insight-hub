from django.urls import path

from .views import (
    DashboardView,
    HomeView,
    ImprovementCreateView,
    ImprovementListView,
    NoticeCenterView,
    QuickSurveyView,
    StatsOverviewView,
    SurveyBuilderView,
    SurveyCreateView,
    SurveyDetailView,
    SurveyManagerView,
    SurveySubmitSuccessView,
    TextAnalysisView,
)

app_name = "feedback"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/forms/", SurveyManagerView.as_view(), name="survey-manager"),
    path("dashboard/forms/new/", SurveyCreateView.as_view(), name="survey-create"),
    path("dashboard/forms/<slug:slug>/builder/", SurveyBuilderView.as_view(), name="survey-builder"),
    path("dashboard/stats/", StatsOverviewView.as_view(), name="stats-overview"),
    path("dashboard/text-analysis/", TextAnalysisView.as_view(), name="text-analysis"),
    path("dashboard/improvements/", ImprovementListView.as_view(), name="improvement-list"),
    path("dashboard/notices/", NoticeCenterView.as_view(), name="notice-center"),
    path("survey/<slug:slug>/", SurveyDetailView.as_view(), name="survey-detail"),
    path("survey/<slug:slug>/quick/", QuickSurveyView.as_view(), name="survey-quick"),
    path("survey/<slug:slug>/success/", SurveySubmitSuccessView.as_view(), name="survey-success"),
    path("survey/<slug:slug>/improvement/new/", ImprovementCreateView.as_view(), name="improvement-create"),
]
