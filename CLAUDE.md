# CLAUDE.md

## 開發規則（重要）

- 每次修改程式碼前，必須先列出修改計畫，等待我確認後才能動手
- 不可以直接修改檔案，一定要先問我

## 我負責的範圍

- 通知中心（Notice Center）：/dashboard/notices/
- 部分顧客中心（Customer Center）：/app/notifications/

## 注意事項

- 不要修改 seed_demo.py
- 測試用假資料請使用 seed_notification_test

---

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Feedback Insight Hub** — a bilingual (Traditional Chinese / English) feedback and survey management platform. Django handles presentation, authentication, and ORM; a Flask microservice handles the feedback domain with analytics. The two services share the same PostgreSQL database (Supabase in production).

## Commands

### Local Development

```bash
# Install dependencies
python -m venv .venv
source .venv/Scripts/activate   # Windows bash
pip install -r requirements.txt

# Initialize database and seed demo data
python manage.py migrate
python manage.py ensure_superuser
python manage.py seed_demo

# Start Flask microservice (port 5001)
python -m flask --app services.feedback_service.app run --host 127.0.0.1 --port 5001

# Start Django dev server (port 8000)
python manage.py runserver
```

### Production (Render)

```bash
# Django
gunicorn config.wsgi:application

# Flask
gunicorn services.feedback_service.app:app --bind 0.0.0.0:10000
```

### Custom Management Commands

```bash
python manage.py ensure_superuser        # Create admin from env vars (ADMIN_USERNAME/EMAIL/PASSWORD)
python manage.py seed_demo               # Seed example survey + keyword categories
python manage.py seed_notification_test  # Seed 4 test users, survey, submissions, improvement dispatch + email
```

## Architecture

### Two-Layer Service Design

```
Django (port 8000)  →  service_client.py  →  Flask microservice (port 5001)
                                        ↘  local_service.py (fallback)
                                              ↓
                                    Shared PostgreSQL (Supabase) / SQLite DB
```

**`feedback/service_client.py`** implements a circuit-breaker pattern: it tries the Flask microservice first, and on failure automatically falls back to `feedback/local_service.py` (which queries the DB via Django ORM). A `disabled_until` timestamp prevents retry storms (default 30s cooldown). If `FEEDBACK_SERVICE_URL` is not set at all, the local provider is used exclusively.

### Key Directories

| Path | Purpose |
|---|---|
| `config/` | Django settings, URLs, WSGI/ASGI |
| `accounts/` | Django app: users, roles, preferences |
| `feedback/` | Django app: surveys, views, service client, local service |
| `services/feedback_service/` | Flask microservice: API routes, SQLAlchemy models, analytics |
| `templates/` | Django HTML templates (all UI) |
| `static/css/app.css` | Single hand-written CSS file, no external framework |

### Flask API Endpoints (`services/feedback_service/app.py`)

- `GET /health` — health check
- `GET /api/home` — homepage stats
- `GET /api/customers/<user_id>/home` — customer dashboard
- `GET /api/customers/<user_id>/notifications` — customer notifications
- `GET /api/dashboard` — manager dashboard metrics
- `GET /api/stats?survey=<slug>` — survey charts and statistical analysis
- `GET /api/text-analysis?survey=<slug>` — keyword frequency analysis
- `POST /api/surveys/<slug>/submissions` — submit survey responses

### Django URL Structure (`feedback/urls.py`)

| URL | View | Name |
|---|---|---|
| `/` | HomeView | `feedback:home` |
| `/app/` | CustomerHomeView | `feedback:customer-home` |
| `/app/notifications/` | CustomerNotificationsView | `feedback:customer-notifications` |
| `/app/notifications/<pk>/read/` | MarkNoticeReadView | `feedback:notice-mark-read` |
| `/dashboard/` | DashboardView | `feedback:dashboard` |
| `/dashboard/forms/` | SurveyManagerView | `feedback:survey-manager` |
| `/dashboard/forms/new/` | SurveyCreateView | `feedback:survey-create` |
| `/dashboard/forms/<slug>/builder/` | SurveyBuilderView | `feedback:survey-builder` |
| `/dashboard/stats/` | StatsOverviewView | `feedback:stats-overview` |
| `/dashboard/text-analysis/` | TextAnalysisView | `feedback:text-analysis` |
| `/dashboard/improvements/` | ImprovementListView | `feedback:improvement-list` |
| `/dashboard/notices/` | NoticeCenterView | `feedback:notice-center` |
| `/dashboard/notices/<pk>/` | NoticeDetailView | `feedback:notice-detail` |
| `/survey/<slug>/` | SurveyDetailView | `feedback:survey-detail` |
| `/survey/<slug>/success/` | SurveySubmitSuccessView | `feedback:survey-success` |
| `/survey/<slug>/improvement/new/` | ImprovementCreateView | `feedback:improvement-create` |
| `/accounts/login/` | — | `accounts:login` |
| `/accounts/logout/` | — | `accounts:logout` |
| `/accounts/signup/` | — | `accounts:signup` |
| `/accounts/preferences/` | — | `accounts:preferences` |

### Roles

Two user roles (`accounts/models.py`): `CUSTOMER` and `MANAGER`. Role-based access is enforced via Django mixins in views (`ManagerRequiredMixin`, `CustomerRequiredMixin`, `DashboardBaseMixin`).

### Survey Access

All surveys require login. `Survey.AccessMode` only has one value:

- `LOGIN = "login"` — authentication required for all survey access

`SurveyDetailView.dispatch` unconditionally redirects unauthenticated users to `/accounts/login/?next=<path>`. There is no anonymous or quick-access mode. The user flow is: scan QR code → redirect to login if not authenticated → fill survey after login.

### Text Analysis

Tokenizes submission text using regex supporting both Chinese characters and English words (2+ chars). Filters a hardcoded stop-word list. Returns top 20 keywords by frequency with `category` field (looked up from `KeywordCategory`). Found in `services/feedback_service/analysis.py` and mirrored in `feedback/local_service.py`.

### Improvement List Page

`/dashboard/improvements/` uses an accordion UI: each survey is a collapsible row. Expanding a survey shows its improvement items and an inline form to add new ones (no page navigation). The inline form POSTs to `/survey/<slug>/improvement/new/`. All interaction is vanilla JS + CSS, no external libraries.

### Manager Workspace Layout

The manager sidebar (`dashboard_base.html`) is fixed: `position: sticky; height: 100vh` on `.manager-sidebar`, with `.manager-shell` set to `height: 100vh; overflow: hidden` and `.manager-main` set to `overflow-y: auto; height: 100vh`. This makes the sidebar stay in place while only the right content area scrolls.

### Signup Form (`/accounts/signup/`)

`CustomerSignUpForm` fields: `username`, `first_name`, `email`, `notification_opt_in`, `password1`, `password2`. `last_name` and `organization` have been removed. The signup page includes a disabled Google login placeholder button (coming soon) above the email form, separated by a divider.

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Required in production |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | — | Comma-separated |
| `DATABASE_URL` | SQLite | PostgreSQL URL for production (Supabase) |
| `FEEDBACK_SERVICE_URL` | — | Flask URL; omit to use local provider only |
| `FEEDBACK_SERVICE_CONNECT_TIMEOUT` | `0.35` | Seconds |
| `FEEDBACK_SERVICE_READ_TIMEOUT` | `0.8` | Seconds |
| `FEEDBACK_SERVICE_FAILURE_COOLDOWN` | `30` | Seconds before retrying Flask |
| `ADMIN_USERNAME` | — | Used by `ensure_superuser` command |
| `ADMIN_EMAIL` | — | Used by `ensure_superuser` command |
| `ADMIN_PASSWORD` | — | Used by `ensure_superuser` command |

## Data Models

**Django ORM** (source of truth): `Survey`, `Question`, `FeedbackSubmission`, `Answer`, `KeywordCategory`, `ImprovementUpdate`, `ImprovementDispatch` in `feedback/models.py`. `User` (extends `AbstractUser`) with `role` and `notification_opt_in` in `accounts/models.py`.

**SQLAlchemy models** in `services/feedback_service/models.py` mirror the Django schema — they read/write the same tables. When adding fields, update both ORMs and create a Django migration.

### ImprovementListView Context

`ImprovementListView.get_context_data` provides `survey_groups`, a list of dicts:

```python
{
    "survey": Survey,           # Survey instance
    "improvements": [...],      # list of ImprovementUpdate for this survey
    "create_url": str,          # reverse("feedback:improvement-create", args=[survey.slug])
}
```

Fetched in 2 queries (no N+1): one for all improvements, one for all surveys; grouped in Python.

## Migrations

| Migration | Description |
|---|---|
| `feedback/0001` – `0004` | Initial schema |
| `feedback/0005` | Remove QUICK/HYBRID choices from Survey.access_mode and FeedbackSubmission.source |
| `feedback/0006` | Data migration: convert existing hybrid/quick records to login |

## Deployment

Deployed on **Render** (see `render.yaml`):
- `feedback-insight-hub` (type: web) — Django, built via `build.sh`
- `feedback-domain-service` (type: pserv) — Flask private service

`build.sh` runs: `pip install`, `migrate`, `ensure_superuser`, `seed_demo`, `collectstatic`.

Static files served by Whitenoise. `DATABASE_URL` must be set manually in Render dashboard for both services (points to Supabase PostgreSQL).

## Dependencies

```
Django==6.0.3
dj-database-url==3.0.1
Flask==3.1.2
gunicorn==23.0.0
psycopg[binary]==3.3.3      # psycopg3, not psycopg2
requests==2.32.5
SQLAlchemy==2.0.43
whitenoise==6.9.0
```

No frontend JS/CSS framework. All UI is custom HTML + `static/css/app.css`.

## 通知系統（Notification System）

### Context Processor

`feedback/context_processors.py` 提供 `unread_notification_count`，對所有已登入的顧客（非 manager）查詢未讀 `ImprovementDispatch` 數量，注入所有 template context，讓 `base.html` 導覽列可直接使用 `{{ unread_notification_count }}`。已在 `config/settings.py` 的 `TEMPLATES.context_processors` 中註冊。

### Email 設定

透過 `.env` 環境變數控制，預設為 console backend（開發用）。正式寄信需設定以下變數：

| 變數 | 值 |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | 你的 Gmail 帳號 |
| `EMAIL_HOST_PASSWORD` | Gmail App Password（16 碼） |
| `DEFAULT_FROM_EMAIL` | 你的 Gmail 帳號 |

Gmail App Password 產生：Google 帳號 → 安全性 → 兩步驟驗證 → 應用程式密碼。

### 導覽列未讀 Badge

`base.html` 顧客端導覽列的「通知」連結帶有 `.nav-badge`，顯示 `{{ unread_notification_count }}`（大於 0 才顯示）。樣式定義在 `static/css/app.css`：紅色圓形、`position: absolute` 定位於連結右上角，帶 `box-shadow` 增加視覺層次。

### AJAX 標記已讀流程

`/app/notifications/` 頁面（`customer_notifications.html`）：

1. 每條通知 row 帶有 `data-pk`、`data-is-read`、`data-survey-url` 屬性
2. 點擊整條通知時，JS 判斷若未讀，向 `/app/notifications/<pk>/read/` 發送 AJAX POST
3. 請求帶 `X-Requested-With: XMLHttpRequest` header，CSRF token 從 cookie 取得
4. `MarkNoticeReadView` 偵測到 AJAX 請求後回傳 `{"ok": True}`（非 AJAX 則 redirect）
5. 前端收到回應後即時更新：移除 `record-row-unread` class、badge 數字 -1、pill 改為「已讀」
6. UI 更新完成後導向 `data-survey-url`（對應問卷詳情頁）
