from django import forms

from .models import ImprovementUpdate, Question, Survey


class SurveyFormBuilder(forms.Form):
    def __init__(self, *args, survey: Survey, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        for question in survey.questions.all():
            self.fields[f"question_{question.id}"] = self._build_field(question)

    def _build_field(self, question: Question):
        common = {
            "label": question.title,
            "required": question.is_required,
            "help_text": question.help_text,
        }
        if question.kind == Question.Kind.SHORT_TEXT:
            return forms.CharField(max_length=255, **common)
        if question.kind == Question.Kind.LONG_TEXT:
            return forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), **common)
        if question.kind == Question.Kind.SINGLE_CHOICE:
            return forms.ChoiceField(choices=[(option, option) for option in question.options], **common)
        if question.kind == Question.Kind.MULTIPLE_CHOICE:
            return forms.MultipleChoiceField(
                choices=[(option, option) for option in question.options],
                widget=forms.CheckboxSelectMultiple,
                **common,
            )
        if question.kind == Question.Kind.INTEGER:
            return forms.IntegerField(**common)
        if question.kind == Question.Kind.DECIMAL:
            return forms.DecimalField(decimal_places=2, max_digits=10, **common)
        if question.kind == Question.Kind.SCALE:
            return forms.IntegerField(min_value=1, max_value=10, **common)
        return forms.CharField(**common)


class QuickAccessForm(forms.Form):
    respondent_name = forms.CharField(label="姓名", max_length=120, required=False)
    respondent_email = forms.EmailField(label="Email", required=False)
    consent_follow_up = forms.BooleanField(label="願意接收後續改善通知", required=False)


class ImprovementUpdateForm(forms.ModelForm):
    class Meta:
        model = ImprovementUpdate
        fields = ("title", "summary", "related_category", "send_global_notice")
        labels = {
            "title": "改善主題",
            "summary": "改善內容摘要",
            "related_category": "關聯分類",
            "send_global_notice": "是否發送通知",
        }


class SurveyCreateForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = (
            "title",
            "slug",
            "description",
            "access_mode",
            "thank_you_email_enabled",
            "improvement_tracking_enabled",
            "is_active",
        )
        labels = {
            "title": "問卷標題",
            "slug": "網址代稱",
            "description": "問卷說明",
            "access_mode": "填答模式",
            "thank_you_email_enabled": "送出後寄送感謝信",
            "improvement_tracking_enabled": "啟用改善追蹤",
            "is_active": "啟用問卷",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class QuestionCreateForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = (
            "title",
            "help_text",
            "kind",
            "data_type",
            "options_text",
            "is_required",
            "enable_keyword_tracking",
            "order",
        )
        labels = {
            "title": "問題標題",
            "help_text": "補充說明",
            "kind": "題型",
            "data_type": "資料型態",
            "options_text": "選項內容",
            "is_required": "必填",
            "enable_keyword_tracking": "啟用文字關鍵字追蹤",
            "order": "排序",
        }
        widgets = {
            "options_text": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "請一行填一個選項\n例如：\n非常滿意\n滿意\n普通",
                }
            ),
            "help_text": forms.TextInput(attrs={"placeholder": "例如：請依照您最近一次使用經驗作答"}),
        }
