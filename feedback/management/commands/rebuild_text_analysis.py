from django.core.management.base import BaseCommand

from feedback.models import Answer, Question
from feedback.text_pipeline import ANALYSIS_VERSION, build_analysis_text, estimate_sentiment_score


class Command(BaseCommand):
    help = "Rebuild analysis_text and sentiment_score for historical text answers."

    def add_arguments(self, parser):
        parser.add_argument("--survey", type=str, default="", help="Optional survey slug filter.")
        parser.add_argument("--dry-run", action="store_true", help="Preview affected rows without writing data.")

    def handle(self, *args, **options):
        queryset = Answer.objects.select_related("question", "question__survey")
        if options["survey"]:
            queryset = queryset.filter(question__survey__slug=options["survey"])
        queryset = queryset.filter(question__kind__in=[Question.Kind.SHORT_TEXT, Question.Kind.LONG_TEXT])

        updated = 0
        skipped = 0
        for answer in queryset.iterator():
            analysis_text = build_analysis_text(answer.value)
            sentiment_score = estimate_sentiment_score(answer.value) if analysis_text else None
            if (
                answer.analysis_text == analysis_text
                and answer.sentiment_score == sentiment_score
                and answer.analysis_version == (ANALYSIS_VERSION if analysis_text else None)
            ):
                skipped += 1
                continue

            updated += 1
            if options["dry_run"]:
                continue

            answer.analysis_text = analysis_text
            answer.sentiment_score = sentiment_score
            answer.analysis_version = ANALYSIS_VERSION if analysis_text else None
            answer.save(update_fields=["analysis_text", "sentiment_score", "analysis_version"])

        mode_label = "DRY-RUN" if options["dry_run"] else "APPLY"
        self.stdout.write(self.style.SUCCESS(f"[{mode_label}] updated={updated}, skipped={skipped}"))
