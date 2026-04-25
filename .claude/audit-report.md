# 全面健檢報告

> 初次檢查：2026-04-20　|　最後更新：2026-04-25

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

> ⚠️ 注意：`SurveyCategory` 目前只有 Django ORM，尚未加入 SQLAlchemy models。若 Flask 需要讀取分類資料，需補上。

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

## 2026-04-25 更新紀錄

### 問卷建立流程重構（commits 82913f7、ef76217）

**目標：** 簡化建立介面，移除使用者不需手動填寫的欄位。

| 變更 | 說明 |
|---|---|
| `SurveyCreateForm` 移除 `slug` | 改由 `form_valid` 用 `slugify(title)` 自動產生，衝突時加流水號 `-2`, `-3`... |
| `SurveyCreateForm` 移除 `access_mode` | 固定寫入 `Survey.AccessMode.LOGIN` |
| `SurveyCreateForm` 移除 `improvement_tracking_enabled` | 固定寫入 `True`；Admin 端設為 `readonly_fields` |
| `survey_create.html` 重設計 | 單欄佈局；`is_active` 改為 toggle UI；`thank_you_email_enabled` 改為 rich checkbox；加 info-callout |
| `app.css` 新增 | `.setting-block`、`.toggle-*`、`.checkbox-label-rich`、`.info-callout` |

---

### 新增 python-dotenv（commit d7d92c2）

- `requirements.txt` 加入 `python-dotenv==1.0.1`
- `config/settings.py` 啟動時自動 `load_dotenv(BASE_DIR / ".env")`
- 本地開發不再需要手動 export 環境變數

---

### 問卷分類功能（commit d7d92c2）

**新增 `SurveyCategory` model：**
- `name`（unique）、`created_at`
- migration `0007_add_survey_category`

**`Survey` 新增 `category` FK：**
- `null=True, blank=True, SET_NULL`
- `SurveyAdmin` 加入 `category` 欄位

**`SurveyCreateForm` 加入 `category`：**
- `ModelChoiceField`，`empty_label="── 選擇分類（選填）──"`

**`SurveyManagerView` 加入排序與篩選：**
- `?sort=newest`（預設）/ `?sort=oldest` / `?sort=title`
- `?category=<id>` 篩選分類
- context 新增：`categories`、`current_sort`、`current_category`

**`survey_manager.html` 更新：**
- 頂部加 toolbar：左側分類 filter-pill，右側排序 `<select>`
- 問卷列加分類 `.pill-category`

**`app.css` 新增：**
- `.manager-toolbar`、`.toolbar-filters`、`.filter-pill`、`.filter-pill-active`、`.sort-select`、`.pill-category`

---

### Survey Builder 三 Tab 重設計（commit 517603f）

**目標：** 將靜態裝飾 tab 改為可切換的真實功能介面。

**Tab 1：題目設定（questions）**
- 左欄（60%）：題目列表 + 每題 inline edit（`action=edit-question`）
  - 點「編輯」展開 edit form，同時只能開一個
  - 刪除按鈕保留
- 右欄（40%）：新增題目 form（原有 `QuestionCreateForm`，不變）

**Tab 2：回覆概況（responses）**
- 顯示回覆總數、最近回覆時間
- 連結到統計分析頁、文字洞察頁

**Tab 3：問卷設定（settings）**
- `SurveyEditForm`（新增）：`title`、`category`、`description`、`is_active`（toggle）、`thank_you_email_enabled`（checkbox）
- slug 唯讀 + 「複製連結」按鈕（`navigator.clipboard`）
- `action=update-survey`

**views.py 變更：**
- `SurveyBuilderView.post` 新增 `edit-question` 和 `update-survey` action
- `get_context_data` 新增 `survey_edit_form`、`latest_response`、`active_tab`
- redirect 帶 `?tab=<key>` 保留 tab 狀態

**forms.py 新增：**
- `SurveyEditForm`（ModelForm，fields 同上）

**app.css 新增：**
- `.tab-bar`、`.tab-btn`、`.tab-btn-active`
- `.builder-layout`（3fr 2fr grid，響應式）
- `.inline-edit-panel`、`.inline-edit-actions`
- `.responses-summary`、`.response-actions`
- `.slug-row`、`.slug-input`

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
| 9efdcef | Fix QUICK/HYBRID remnants, add CSRF_TRUSTED_ORIGINS, remove orphan CSS brace |
| 82913f7 | Remove slug/access_mode from survey create form, auto-generate slug from title |
| ef76217 | Enforce improvement_tracking, redesign survey create form with toggle and callout |
| d7d92c2 | Add survey category with filter/sort, redesign create form layout |
| 517603f | Implement tabbed survey builder with inline edit, responses, and settings tab |

---

## 目前待處理事項

| 優先 | 問題 | 說明 |
|---|---|---|
| ⚠️ 低 | Flask vs Django text 類型建議文字略有出入 | `recommend_analysis` 對 text/其他 type 文字不同，不影響功能 |
| ⚠️ 低 | `SurveyCategory` 未加入 SQLAlchemy models | Flask 目前不需讀取分類，但若日後 API 要回傳分類資訊需補上 |

---

## 目前架構狀態

**Survey 存取模式：** 只剩 `LOGIN`，所有問卷必須登入才能填答。流程：掃 QR code → 未登入跳登入頁（帶 `?next=` 參數）→ 登入後繼續填。

**Survey 建立流程：** 使用者只需填 title / category / description / 功能開關，slug 自動產生，access_mode 和 improvement_tracking_enabled 由 view 強制寫入。

**Survey Builder：** 三 Tab 架構（題目設定 / 回覆概況 / 問卷設定），每個 tab 都有對應內容和 POST handler，tab 狀態透過 `?tab=` query param 保留。

**Manager Workspace：** 左側導覽面板固定不動，右側內容區獨立捲動。

**改善追蹤頁：** Accordion UI，按問卷展開，inline 新增表單，不跳頁。

**註冊頁：** 欄位精簡為 username / first_name / email / password / notification_opt_in，頂部有 Google 登入預留位（disabled）。

**資料庫：** Supabase PostgreSQL，`DATABASE_URL` 需在 Render dashboard 兩個服務各自設定。Migration 0007 已加入 SurveyCategory。

**本地開發：** `python-dotenv` 自動載入 `.env`，不需手動 export。
