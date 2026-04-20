# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Feedback Insight Hub** — a bilingual (Traditional Chinese / English) feedback and survey management platform. Django handles presentation, authentication, and ORM; a Flask microservice handles the feedback domain with analytics. The two services share the same database.

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
python manage.py ensure_superuser   # Create admin from env vars
python manage.py seed_demo          # Seed example survey + keyword categories
```

## Architecture

### Two-Layer Service Design

```
Django (port 8000)  →  service_client.py  →  Flask microservice (port 5001)
                                        ↘  local_service.py (fallback)
                                              ↓
                                    Shared PostgreSQL / SQLite DB
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

### Flask API Endpoints (`services/feedback_service/app.py`)

- `GET /health` — health check
- `GET /api/home` — homepage stats
- `GET /api/customers/<user_id>/home` — customer dashboard
- `GET /api/customers/<user_id>/notifications` — customer notifications
- `GET /api/dashboard` — manager dashboard metrics
- `GET /api/stats?survey=<slug>` — survey charts and statistical analysis
- `GET /api/text-analysis?survey=<slug>` — keyword frequency analysis
- `POST /api/surveys/<slug>/submissions` — submit survey responses

### Django URL Structure (`config/urls.py`)

Public routes: landing page, survey form (`/s/<slug>/`), quick survey (`/q/<slug>/`).
Customer routes: `/customer/home/`, `/customer/notifications/`.
Manager routes: `/manager/dashboard/`, `/manager/surveys/`, `/manager/builder/`, `/manager/stats/`, `/manager/text-analysis/`, `/manager/improvements/`, `/manager/notices/`.
Auth routes: `/auth/login/`, `/auth/logout/`, `/auth/signup/`.

### Roles

Two user roles (`accounts/models.py`): `CUSTOMER` and `MANAGER`. Role-based access is enforced via Django mixins in views.

### Survey Access Modes

- `LOGIN` — requires authentication
- `QUICK` — anonymous via slug URL
- `HYBRID` — both modes accepted

### Text Analysis

Tokenizes submission text using regex supporting both Chinese characters and English words (2+ chars). Filters a hardcoded stop-word list. Returns top 20 keywords by frequency. Found in `services/feedback_service/app.py` and mirrored in `feedback/local_service.py`.

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Required in production |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | — | Comma-separated |
| `DATABASE_URL` | SQLite | PostgreSQL URL for production |
| `FEEDBACK_SERVICE_URL` | — | Flask URL; omit to use local provider only |
| `FEEDBACK_SERVICE_CONNECT_TIMEOUT` | `0.35` | Seconds |
| `FEEDBACK_SERVICE_READ_TIMEOUT` | `0.8` | Seconds |
| `FEEDBACK_SERVICE_FAILURE_COOLDOWN` | `30` | Seconds before retrying Flask |
| `ADMIN_USERNAME/EMAIL/PASSWORD` | — | Used by `ensure_superuser` command |

## Data Models

**Django ORM** (source of truth): `Survey`, `Question`, `FeedbackSubmission`, `Answer`, `KeywordCategory`, `ImprovementUpdate`, `ImprovementDispatch` in `feedback/models.py`. `User` (extends `AbstractUser`) with `role` and `notification_opt_in` in `accounts/models.py`.

**SQLAlchemy models** in `services/feedback_service/models.py` mirror the Django schema — they read/write the same tables. When adding fields, update both ORMs and create a Django migration.

## Deployment

Deployed on **Render** (see `render.yaml`). The build script is `build.sh`. Static files served by Whitenoise. The Flask service is a private service (not publicly accessible); Django communicates with it via internal URL.
