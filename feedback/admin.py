from django.contrib import admin

from .models import (
    Answer,
    FeedbackSubmission,
    ImprovementDispatch,
    ImprovementUpdate,
    KeywordCategory,
    Question,
    Survey,
)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "access_mode", "is_active", "updated_at")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuestionInline]
    readonly_fields = ("improvement_tracking_enabled",)
    fields = (
        "title", "slug", "description", "access_mode",
        "thank_you_email_enabled", "is_active",
        "improvement_tracking_enabled",
    )


@admin.register(FeedbackSubmission)
class FeedbackSubmissionAdmin(admin.ModelAdmin):
    list_display = ("survey", "display_name", "respondent_email", "source", "submitted_at")
    list_filter = ("survey", "source", "consent_follow_up")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "submission", "value")


admin.site.register(KeywordCategory)
admin.site.register(ImprovementUpdate)
admin.site.register(ImprovementDispatch)
