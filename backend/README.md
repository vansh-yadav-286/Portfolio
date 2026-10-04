# Portfolio API (backend)

FastAPI backend for the portfolio: projects, certificates, contact form and analytics, with JWT-based auth and role-based admin access. PostgreSQL via SQLAlchemy; migrations live in [`../database`](../database).

## Architecture

```
frontend/  (HTML/CSS/JS)
    ↓ REST
backend/app/routes      ← HTTP layer, request/response shapes
    ↓
backend/app/schemas     ← Pydantic validation
    ↓
backend/app/services    ← business logic
    ↓
backend/app/models      ← SQLAlchemy ORM
    ↓
PostgreSQL
```

```
app/
├── main.py            # app wiring: CORS, exception handlers, routers, lifespan
├── core/
│   ├── config.py       # Settings (env vars)
│   ├── security.py     # password hashing, JWT encode/decode
│   ├── dependencies.py # get_current_user / get_current_admin
│   └── rate_limit.py   # slowapi limiter (used on /api/auth/login)
├── routes/             # one file per resource, thin HTTP layer
├── services/           # business logic, called by routes
├── schemas/            # Pydantic request/response models
├── models/             # SQLAlchemy ORM models
├── database/           # engine/session + declarative Base
└── utils/helpers.py    # success_response(), api_error()
tests/                  # pytest, one file per resource
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values

cd ../database
alembic upgrade head    # creates the schema
psql "$DATABASE_URL" -f seeds/seed.sql   # optional: seed sample projects/certificates

cd ../backend
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs` and `http://localhost:8000/redoc`.

The admin account (role `admin`) is created automatically on first startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD` — no manual seeding needed.

**Note:** the admin account is only created if the email does not exist yet. Changing `ADMIN_PASSWORD` later does **not** update the existing account; change the password in the database (or delete the row and restart) instead. Log in at `POST /api/auth/login` with those credentials to use the admin dashboard.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

CI runs the same suite on every push and pull request that touches `backend/` (see `.github/workflows/backend-tests.yml`).

Tests run against a throwaway SQLite database (`tests/conftest.py`), independent of your dev Postgres instance.

## API

All responses use a consistent envelope:

```json
{ "success": true, "message": "...", "data": { ... } }
{ "success": false, "message": "..." }
```

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/register` | public |
| POST | `/api/auth/login` | public (rate-limited: 5/min) |
| GET | `/api/auth/me` | any authenticated user |
| POST | `/api/auth/logout` | any authenticated user |
| GET | `/api/projects`, `/api/projects/{id}` | public |
| POST/PUT/DELETE | `/api/projects[/{id}]` | admin |
| GET | `/api/certificates`, `/api/certificates/{id}` | public |
| POST/PUT/DELETE | `/api/certificates[/{id}]` | admin |
| POST | `/api/contact` | public |
| GET/PATCH/DELETE | `/api/contact[/{id}]` | admin |
| POST | `/api/analytics/visit` | public |
| GET | `/api/analytics` | admin |

## Security

- Passwords hashed with bcrypt (passlib).
- JWT (HS256) via OAuth2PasswordBearer; admin-only routes are guarded by a role check (`app/core/dependencies.py`).
- `/api/auth/login` is rate-limited (slowapi) against brute-force attempts.
- CORS allows only `FRONTEND_URL` — never `*` — since the API is authenticated.
- All exceptions are caught centrally (`app/main.py`) so stack traces and internals are never returned to the client.

## Deploying to Render

This service is deployed on **Render**. Do not use Railway. See [`../render.yaml`](../render.yaml) for the full blueprint (run from the repo root, since it builds both `backend/` and `database/`).

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo's `render.yaml`.
3. Build command: `pip install -r backend/requirements.txt && cd database && alembic upgrade head`
4. Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Attach the managed PostgreSQL instance (the blueprint provisions one and injects `DATABASE_URL` automatically).
6. Set the remaining environment variables in the Render dashboard (never commit them): `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_URL` (your GitHub Pages origin), `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

Render supplies `$PORT` at runtime; the start command binds to it rather than a hardcoded port.

## Frontend integration

The frontend calls this API through a single `API_BASE_URL` constant (`frontend/js/config.js`) — never hardcoded inline. Point it at `http://localhost:8000` in development and the Render URL in production.
