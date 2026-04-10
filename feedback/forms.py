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
    consent_follow_up = forms.BooleanField(label="同意後續聯繫", required=False)


class ImprovementUpdateForm(forms.ModelForm):
    class Meta:
        model = ImprovementUpdate
        fields = ("title", "summary", "related_category", "send_global_notice")
