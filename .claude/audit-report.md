# 全面健檢報告

> 初次檢查：2026-04-20　|　最後更新：2026-04-21

---

## Task 1：Model 欄位對齊（feedback/models.py vs services/feedback_service/models.py）

所有欄位已對齊，無待處理問題。

| Model | 狀態 |
|---|---|
| Survey | ✅ 全部對齊（slug 已補 unique=True） |
| Question | ✅ |
| FeedbackSubmission | ✅ |
| ImprovementUpdate | ✅ |
| ImprovementDispatch | ✅ |
| KeywordCategory | ✅ 已新增 SQLAlchemy model |

**blank=True vs NOT nullable 說明：** Django `blank=True` 是 form validation 層，不是 DB nullable。這些欄位 Django 端沒有 `null=True`，DB 實際 NOT NULL、寫入空字串。SQLAlchemy `Mapped[str]` 正確反映，無需修改。

---

## Task 2：業務邏輯一致性（Flask vs Django local_service）

| 項目 | 狀態 |
|---|---|
| 斷詞 regex | ✅ 一致 |
| 停用字 | ✅ 一致 |
| Top-N 數量 | ✅ 一致 |
| keyword.category 欄位 | ✅ 已修（Flask 補上） |
| data_type 顯示語言 | ✅ 已修（Flask 改回中文 label） |
| text 類型建議文字 | ⚠️ 輕微不一致（低優先，不影響功能） |

---

## Task 3：Template vs 後端資料結構

全部 ✅，無待處理問題。

---

## 全部修復與改動紀錄

| commit | 內容 |
|---|---|
| c562d5a | Flask text-analysis 補 category；stats data_type 改中文 label；新增 KeywordCategory SQLAlchemy model |
| 88b37d5 | Survey.slug SQLAlchemy 補 unique=True |
| 31d2f24 | local_service.get_dashboard_payload() NameError 修復（surveys 未定義，/dashboard/ 500） |
| a1458fa | 改善追蹤頁重設計：accordion UI、inline 新增表單、ImprovementListView 改 survey_groups context |
| 6b90257 | 註冊頁重設計：Google 登入預留位、兩層欄位結構 |
| ff99d94 | 修復 checkbox 寬度與文字換行（input[type=checkbox] 被全域樣式影響） |
| e4f38b6 | 註冊表單移除 last_name 和 organization |
| 3913cdb | 移除 QUICK/HYBRID access mode，統一改為 LOGIN；移除 QuickSurveyView；migration 0005+0006 |
| 4cf1efe | seed_demo.py 修復（HYBRID → LOGIN） |
| 446d0a5 | Manager sidebar 固定不隨頁面捲動（sticky + 100vh） |

---

## 目前待處理事項

| 優先 | 問題 | 說明 |
|---|---|---|
| ⚠️ 低 | Flask vs Django text 類型建議文字略有出入 | `recommend_analysis` 對 text/其他 type 文字不同，不影響功能 |

---

## 目前架構狀態

**Survey 存取模式：** 只剩 `LOGIN`，所有問卷必須登入才能填答。流程：掃 QR code → 未登入跳登入頁（帶 `?next=` 參數）→ 登入後繼續填。

**Manager Workspace：** 左側導覽面板固定不動，右側內容區獨立捲動。

**改善追蹤頁：** Accordion UI，按問卷展開，inline 新增表單，不跳頁。

**註冊頁：** 欄位精簡為 username / first_name / email / password / notification_opt_in，頂部有 Google 登入預留位（disabled）。

**資料庫：** Supabase PostgreSQL，`DATABASE_URL` 需在 Render dashboard 兩個服務各自設定。Migration 0006 已將既有 hybrid/quick 資料轉為 login。
