import os
import sys
import random
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from feedback.models import Survey, Question, FeedbackSubmission, Answer

def generate_perfect_demo_data():
    print("[1/4] 清除舊有 Demo 問卷...")
    Survey.objects.filter(slug="demo-2026-q1").delete()

    print("[2/4] 建立 Demo 問卷...")
    survey = Survey.objects.create(
        title="2026 Q1 跨部門系統體驗調查",
        slug="demo-2026-q1",
        description="本問卷專為展示自動化統計推論引擎（ANOVA / t-test）所設計。",
        improvement_tracking_enabled=True,
        thank_you_email_enabled=False,
        is_active=True,
    )

    print("[3/4] 建立題目...")
    q_dept = Question.objects.create(
        survey=survey,
        title="您的所屬單位",
        kind="single_choice",
        data_type="nominal",
        options_text="研發部\n行銷部\n業務部",
        order=1,
        is_required=True,
    )

    q_score = Question.objects.create(
        survey=survey,
        title="系統整體流暢度評分（1-10分）",
        kind="integer",
        data_type="continuous",
        order=2,
        is_required=True,
    )

    print("[4/4] 灌入回覆資料...")
    strategies = {
        "研發部": (7, 10),
        "行銷部": (2, 5),
        "業務部": (5, 8),
    }

    for dept, (lo, hi) in strategies.items():
        for i in range(15):
            sub = FeedbackSubmission.objects.create(
                survey=survey,
                respondent_name=f"{dept}測試員_{i+1}",
                consent_follow_up=True,
            )
            Answer.objects.create(
                submission=sub, question=q_dept, value=dept
            )
            Answer.objects.create(
                submission=sub, question=q_score, value=str(random.randint(lo, hi))
            )

    count = FeedbackSubmission.objects.filter(survey=survey).count()
    print(f"[OK] 完成！共建立 {count} 筆回覆")
    print("     前往統計分析選擇「2026 Q1 跨部門系統體驗調查」查看結果")

if __name__ == "__main__":
    generate_perfect_demo_data()
