# CLAUDE.md

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
python manage.py ensure_superuser   # Create admin from env vars (ADMIN_USERNAME/EMAIL/PASSWORD)
python manage.py seed_demo          # Seed example survey + keyword categories
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
| `/dashboard/` | DashboardView | `feedback:dashboard` |
| `/dashboard/forms/` | SurveyManagerView | `feedback:survey-manager` |
| `/dashboard/forms/new/` | SurveyCreateView | `feedback:survey-create` |
| `/dashboard/forms/<slug>/builder/` | SurveyBuilderView | `feedback:survey-builder` |
| `/dashboard/stats/` | StatsOverviewView | `feedback:stats-overview` |
| `/dashboard/text-analysis/` | TextAnalysisView | `feedback:text-analysis` |
| `/dashboard/improvements/` | ImprovementListView | `feedback:improvement-list` |
| `/dashboard/notices/` | NoticeCenterView | `feedback:notice-center` |
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
