from collections import Counter
import re
from statistics import mean


ACCESS_MODE_LABELS = {
    "login": "登入後填答",
    "quick": "快速填答",
    "hybrid": "雙入口模式",
}

DATA_TYPE_LABELS = {
    "nominal": "名目",
    "ordinal": "順序",
    "discrete": "離散",
    "continuous": "連續",
    "text": "文字",
}

STOP_WORDS = {
    "我們",
    "你們",
    "這個",
    "那個",
    "非常",
    "feedback",
    "問卷",
    "改善",
}


def access_mode_label(value: str) -> str:
    return ACCESS_MODE_LABELS.get(value, value)


def tokenize_feedback(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", (text or "").lower())
    return [token for token in tokens if token not in STOP_WORDS]


def summarize_keywords(answer_values: list[str], category_map: dict[str, str] | None = None) -> list[dict]:
    counts = Counter()
    for value in answer_values:
        counts.update(tokenize_feedback(value))
    category_map = category_map or {}
    return [
        {"keyword": word, "count": count, "category": category_map.get(word, "未分類")}
        for word, count in counts.most_common(20)
    ]


def summarize_numeric(values: list[float]) -> dict | None:
    if not values:
        return None
    return {
        "count": len(values),
        "avg": round(mean(values), 2),
        "min": min(values),
        "max": max(values),
    }


def build_dashboard_insights(*, total_surveys: int, total_submissions: int, total_improvements: int, top_survey_title: str | None):
    avg_submissions = round(total_submissions / total_surveys, 1) if total_surveys else 0
    return [
        {
            "title": "目前營運量",
            "body": f"系統現有 {total_surveys} 份問卷、累積 {total_submissions} 份回覆，平均每份問卷 {avg_submissions} 份有效回應。",
            "tone": "neutral",
        },
        {
            "title": "改善閉環進度",
            "body": f"已建立 {total_improvements} 則改善項目，可直接延伸到顧客通知、進度追蹤與管理端公告。",
            "tone": "positive" if total_improvements else "neutral",
        },
        {
            "title": "最值得優先檢視的問卷",
            "body": f"{top_survey_title or '目前尚無熱門問卷'} 最接近第一線聲量，可優先作為營運和文字分析入口。",
            "tone": "attention" if top_survey_title else "neutral",
        },
    ]
