from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from feedback.models import Answer, Survey
from feedback.text_pipeline import tokenize_feedback


class Command(BaseCommand):
    help = "列出指定問卷中尚未分類的高頻關鍵詞。"

    def add_arguments(self, parser):
        parser.add_argument("--survey", type=str, required=True, help="問卷 slug，例如 beverage-feedback。")
        parser.add_argument("--limit", type=int, default=30, help="輸出前 N 個關鍵詞，預設 30。")
        parser.add_argument("--min-count", type=int, default=1, help="最低出現次數門檻，預設 1。")

    def handle(self, *args, **options):
        slug = options["survey"]
        limit = options["limit"]
        min_count = options["min_count"]

        if limit <= 0:
            raise CommandError("--limit 必須大於 0。")
        if min_count <= 0:
            raise CommandError("--min-count 必須大於 0。")

        survey = Survey.objects.filter(slug=slug).first()
        if not survey:
            raise CommandError(f"找不到 slug 為 '{slug}' 的問卷。")

        categorized = set(
            survey.keyword_categories.values_list("keyword", flat=True)
        )
        answer_rows = Answer.objects.filter(
            question__survey=survey,
            question__enable_keyword_tracking=True,
        ).values_list("analysis_text", "value")

        counts = Counter()
        for analysis_text, value in answer_rows:
            text = analysis_text or value or ""
            for token in tokenize_feedback(text):
                if token not in categorized:
                    counts[token] += 1

        candidates = [(keyword, total) for keyword, total in counts.most_common() if total >= min_count]
        if not candidates:
            self.stdout.write(self.style.WARNING("沒有找到符合條件的未分類關鍵詞。"))
            return

        self.stdout.write(self.style.SUCCESS(f"問卷：{survey.title} ({survey.slug})"))
        self.stdout.write(f"未分類關鍵詞（前 {min(limit, len(candidates))} 筆，min-count={min_count}）")
        for idx, (keyword, total) in enumerate(candidates[:limit], start=1):
            self.stdout.write(f"{idx:>2}. {keyword} ({total})")
