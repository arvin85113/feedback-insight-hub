import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from feedback.models import KeywordCategory, Question, Survey


class Command(BaseCommand):
    help = "建立飲料店情境的示範問卷與關鍵字分類。"

    def handle(self, *args, **options):
        survey, created = Survey.objects.get_or_create(
            slug="beverage-feedback",
            defaults={
                "title": "飲料店顧客體驗回饋調查",
                "description": "蒐集顧客對甜度、口感、等待時間與服務品質的回饋。",
                "access_mode": Survey.AccessMode.LOGIN,
            },
        )

        questions = [
            {
                "order": 1,
                "title": "本次整體滿意度（1-10）",
                "kind": Question.Kind.SCALE,
                "data_type": Question.DataType.CONTINUOUS,
                "help_text": "1 代表非常不滿意，10 代表非常滿意",
            },
            {
                "order": 2,
                "title": "您本次購買的主要品項",
                "kind": Question.Kind.SINGLE_CHOICE,
                "data_type": Question.DataType.NOMINAL,
                "options_text": "紅茶\n綠茶\n奶茶\n水果茶\n咖啡",
            },
            {
                "order": 3,
                "title": "出杯等待時間感受",
                "kind": Question.Kind.SINGLE_CHOICE,
                "data_type": Question.DataType.ORDINAL,
                "options_text": "非常快\n可接受\n稍慢\n太慢",
            },
            {
                "order": 4,
                "title": "您最在意的店內體驗面向（可複選）",
                "kind": Question.Kind.MULTIPLE_CHOICE,
                "data_type": Question.DataType.NOMINAL,
                "options_text": "甜度冰量\n配料口感\n價格\n店員服務\n門市環境",
            },
            {
                "order": 5,
                "title": "請描述您希望優先改善的地方",
                "kind": Question.Kind.LONG_TEXT,
                "data_type": Question.DataType.TEXT,
                "enable_keyword_tracking": True,
            },
        ]

        for question in questions:
            Question.objects.update_or_create(
                survey=survey,
                order=question["order"],
                defaults=question,
            )

        map_path = Path(__file__).resolve().parents[2] / "data" / "keyword_category_map.json"
        try:
            payload = json.loads(map_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CommandError(f"找不到分類對照檔案: {map_path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"分類對照 JSON 格式錯誤: {exc}") from exc

        threshold = int(payload.get("threshold", 1))
        mappings = payload.get("mappings", {})
        if not isinstance(mappings, dict) or not mappings:
            raise CommandError("keyword_category_map.json 內的 mappings 必須是非空物件。")

        for keyword, category in mappings.items():
            KeywordCategory.objects.update_or_create(
                survey=survey,
                keyword=str(keyword).strip(),
                defaults={"category": str(category).strip(), "threshold": threshold},
            )

        status = "已建立" if created else "已更新"
        self.stdout.write(self.style.SUCCESS(f"{status}飲料店示範問卷：{survey.title} ({survey.slug})"))
