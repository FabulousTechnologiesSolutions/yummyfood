# FoodApp Backend

Django 5.2 + DRF project skeleton (Phase 1 — discovery & promotion). No domain models or APIs yet.

## Stack

- Django / Django REST Framework / SimpleJWT
- PostgreSQL · Redis · Celery · Channels
- OpenAPI via drf-spectacular
- Docker Compose (`web`, `celery`, `celery-beat`, `db`, `redis`)

## Quick start (Docker)

```bash
cp .env.example .env   # or use the committed .env for local docker defaults
docker compose up --build
```

Services:

| Service | URL / port |
|---|---|
| API (uvicorn ASGI) | http://localhost:6060 |
| Swagger UI | http://localhost:6060/api/docs/ |
| ReDoc | http://localhost:6060/api/redoc/ |
| Django admin | http://localhost:6060/admin/ |
| Postgres (host) | localhost:5437 (`foodapp` / `foodapp`) |
| Redis (host) | localhost:6370 |

Copy [.env.example](.env.example) → `.env` for local defaults (same keys as the reference project).

## Local (without Docker)

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# point at compose-published Postgres if needed:
# POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5437
python manage.py migrate
uvicorn conf.asgi:application --host 0.0.0.0 --port 6060
```

## Project layout

```
conf/          # settings, urls, asgi/wsgi, celery
apps/          # domain apps (skeleton only)
core/          # shared stubs (auth, pagination, storage, …)
tests/         # pytest packages (empty stubs)
backend-docs/  # per-app documentation
BACKEND-SPEC.md
```

Settings load from `DJANGO_ENV` / `ENVIRONMENT`: `development` (default), `production`, `testing`.

## Spec & docs

- Master specification: [`BACKEND-SPEC.md`](BACKEND-SPEC.md)
- App guides: [`backend-docs/`](backend-docs/)
