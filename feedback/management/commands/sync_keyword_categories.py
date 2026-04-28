import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from feedback.models import KeywordCategory, Survey


class Command(BaseCommand):
    help = "從 JSON 檔同步 keyword-category 對照到 KeywordCategory。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="feedback/data/keyword_category_map.json",
            help="JSON 檔路徑（相對專案根目錄或絕對路徑）。",
        )
        parser.add_argument("--survey", type=str, default="", help="覆寫 JSON 內 survey slug。")
        parser.add_argument("--threshold", type=int, default=-1, help="覆寫 JSON 內 threshold。")
        parser.add_argument("--dry-run", action="store_true", help="只預覽，不寫入。")

    def handle(self, *args, **options):
        file_arg = options["file"]
        path = Path(file_arg)
        if not path.is_absolute():
            path = Path.cwd() / file_arg
        if not path.exists():
            raise CommandError(f"找不到檔案: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON 格式錯誤: {exc}") from exc

        mappings = payload.get("mappings")
        if not isinstance(mappings, dict) or not mappings:
            raise CommandError("mappings 必須是非空物件。")

        survey_slug = options["survey"] or payload.get("survey")
        if not survey_slug:
            raise CommandError("請提供 survey slug（JSON survey 欄位或 --survey）。")

        threshold = options["threshold"] if options["threshold"] >= 0 else payload.get("threshold", 1)
        if threshold < 0:
            raise CommandError("threshold 不能小於 0。")

        survey = Survey.objects.filter(slug=survey_slug).first()
        if not survey:
            raise CommandError(f"找不到問卷 slug: {survey_slug}")

        created_or_updated = 0
        for keyword, category in mappings.items():
            if not keyword or not category:
                continue
            created_or_updated += 1
            if options["dry_run"]:
                continue
            KeywordCategory.objects.update_or_create(
                survey=survey,
                keyword=str(keyword).strip(),
                defaults={
                    "category": str(category).strip(),
                    "threshold": threshold,
                },
            )

        mode = "DRY-RUN" if options["dry_run"] else "APPLY"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode}] survey={survey.slug}, threshold={threshold}, mappings={created_or_updated}"
            )
        )
