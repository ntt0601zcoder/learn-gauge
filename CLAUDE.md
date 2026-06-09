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

# Tests (Django test runner; ml_clo + DB are mocked, so no model file or DB needed)
venv/bin/python manage.py test                                         # all tests
venv/bin/python manage.py test learngaugeapis.tests.test_predict_view  # one module
venv/bin/python manage.py test learngaugeapis.tests.test_predict_view.PredictStudentTests.test_predict_student_success  # one test

# Docker (bundles migrate + gunicorn; mounts ./data and ./models, sets ML_* env)
docker compose up --build
```

`requirements.txt` pins the **`ml-clo`** ML package from GitHub (`git+https://github.com/ngocmai-26/modelAI.git`). It is an optional dependency — the app degrades gracefully (prediction endpoints return 503) when it is not installed, so most code can run without it.

## Architecture

**learn-gauge** is a Django 5.1 REST API for educational assessment management — courses, exams, student performance tracking, and AI-based CLO score prediction. API docs are at `/swagger/` (drf-yasg); health check at `/health/`.

### Project layout

- `learngauge/` — Django project config: settings, root URL router, WSGI/ASGI
- `learngaugeapis/` — single Django app containing all domain logic:
  - `models/` — 9 core models (see below)
  - `views/` — DRF ViewSets, one file per resource
  - `serializers/` — DRF serializers for request/response shaping
  - `middlewares/` — JWT auth enforcement and role-based permission classes
  - `helpers/` — stateless utilities: OTP, email (`send_html_email`), unified responses (`RestResponse`), pagination
  - `const/` — Python enums: `ExamFormat` (ESSAY/PRACTICE/WRITTEN/MCQ) and semester types
  - `errors/` — custom DRF exception classes
  - `ml_pipeline.py` — process-global ML pipeline holder (see ML subsystem below)
  - `tests/` — Django `TestCase` suites (currently covers `PredictView`)

### Domain model relationships

```text
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
- **Custom JWT**: `learngaugeapis/middlewares/` overrides simplejwt defaults to attach `role` and `user_id` to the token payload. Access token lifetime is 180 minutes.
- **Grade calculation**: automatic A–F / 0–10 conversion happens in serializer `create`/`update` methods (`serializers/exam.py`, `serializers/exam_result.py`).
- **Unified responses**: views return `RestResponse(...).response` (from `helpers/response.py`) rather than raw DRF `Response`, giving every endpoint a consistent envelope.

### ML prediction subsystem (`ml_clo`)

A separate concern from CRUD, wired through three pieces:

- **`ml_pipeline.py`** holds two process-global pipeline singletons (`PredictionPipeline`, `AnalysisPipeline`) behind a `threading.Lock`. `initialize_pipelines()` loads them once and `reload_pipelines()` atomically swaps them after a retrain. All `ml_clo` imports are wrapped in `try/except ImportError` so the module loads even without the package.
- **`apps.py` `ready()`** calls `initialize_pipelines()` at startup **only if** `ML_MODEL_PATH` and `ML_DATA_DIR` are configured. With no config (or no package), pipelines stay `None`.
- **`views/predict.py` `PredictView`** exposes POST `predict/student`, `predict/class`, and `predict/train`. Endpoints return **503** when the pipeline is `None` (not ready), **400** on `DataValidationError`, **500** on `ModelLoadError`/`PredictionError`. `train` spawns a daemon `threading.Thread` running the `TrainingPipeline`, then hot-reloads via `reload_pipelines()`.

The model lives at `models/model.joblib`; training/prediction read fixed-named `.xlsx` files from `ML_DATA_DIR` (the `data/` folder — e.g. `DiemTong.xlsx`, `nhankhau.xlsx`, `PPGDfull.xlsx`). See `ai_integration_guideline.md` (Vietnamese) for the full `ml_clo` data contract and output schemas.

### External dependencies

| Service | Purpose | Config |
|---|---|---|
| Relational DB (MySQL or PostgreSQL) | Primary database | Discrete `DATABASE_ENGINE`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` (default 3306), `DATABASE_SCHEMA` env vars. `ENGINE` is `django.db.backends.{DATABASE_ENGINE}`; both `psycopg[binary]` and `PyMySQL` drivers are installed. |
| Redis Cloud | Django cache backend | `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD` env vars |
| Gmail SMTP | OTP / notification emails | `EMAIL_*` env vars |
| BetterStack Logtail | Centralized logging | `LOGTAIL_TOKEN` env var |
| `ml_clo` model | CLO score prediction/analysis | `ML_MODEL_PATH`, `ML_DATA_DIR` env vars (optional; absent → prediction disabled) |

All secrets are loaded from `.env` via `python-decouple` (`config(...)`).
