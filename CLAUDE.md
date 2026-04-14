# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
make install        # Create venv and install dependencies from requirements.txt
make run            # Run Django development server (uses venv/bin/python)
make fresh          # install + run
make clean          # Uninstall hsmh_model module from venv

# Django management (using venv python)
venv/bin/python manage.py migrate
venv/bin/python manage.py makemigrations
venv/bin/python manage.py createsuperuser
venv/bin/python manage.py runserver
```

No test suite is configured in this project.

## Architecture

**learn-gauge** is a Django 5.1 REST API for educational assessment management — courses, exams, and student performance tracking.

### Project layout

- `learngauge/` — Django project config: settings, root URL router, WSGI/ASGI
- `learngaugeapis/` — single Django app containing all domain logic:
  - `models/` — 9 core models (see below)
  - `views/` — DRF ViewSets, one file per resource
  - `serializers/` — DRF serializers for request/response shaping
  - `middlewares/` — JWT auth enforcement and role-based permission classes
  - `helpers/` — stateless utilities: OTP, Firebase uploads, email, pagination
  - `const/` — Python enums (exam formats, semester types, grade scales)
  - `errors/` — custom DRF exception classes

### Domain model relationships

```
AcademicProgram → Major → Course
                         ↓
                       Class (semester instance, taught by a teacher User)
                         ↓
                  CLOType (learning objective with evaluation weight)
                         ↓
                       Exam (assessment linked to class + CLOType)
                         ↓
              ExamResult / EssayExamResult (per-student scores)
```

`User` has a `role` field: `root`, `teacher`, or `student`. Access control is enforced in middleware and permission classes, not at the model layer.

### Key design patterns

- **Bulk Excel import**: `ExamViewSet` accepts `.xlsx` uploads (via openpyxl) and bulk-creates `ExamResult` rows. The import logic lives in the viewset, not a separate service.
- **Annotated QuerySets**: exam result querysets use Django `annotate()` to compute passing rates, averages, and difficulty breakdowns at the DB layer (not in Python).
- **Custom JWT**: `learngaugeapis/middlewares/` overrides simplejwt defaults to attach `role` and `user_id` to the token payload. Token lifetime is 180 minutes.
- **Grade calculation**: automatic A–F / 0–10 conversion happens in the serializer `create`/`update` methods.

### External dependencies

| Service | Purpose | Config |
|---|---|---|
| PostgreSQL (Render) | Primary database | `DATABASE_URL` env var |
| Redis Cloud | Django cache backend | `REDIS_URL` env var |
| Firebase Storage | File uploads | `FIREBASE_*` env vars |
| Gmail SMTP | OTP / notification emails | `EMAIL_*` env vars |
| BetterStack Logtail | Centralized logging | `LOGTAIL_TOKEN` env var |

All secrets are loaded from `.env` via `python-dotenv`. API docs are at `/swagger/` (drf-yasg).
