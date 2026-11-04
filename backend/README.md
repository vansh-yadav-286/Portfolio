# Portfolio API (backend)

FastAPI backend for the portfolio: projects, certificates, contact form and analytics, with JWT-based auth and role-based admin access. PostgreSQL (hosted on Supabase) via SQLAlchemy; schema migrations live in [`../supabase/migrations`](../supabase/migrations).

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
cp .env.example .env   # fill in real values, including your Supabase DATABASE_URL

psql "$DATABASE_URL" -f ../supabase/migrations/0001_init.sql   # creates the schema

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
| GET | `/health` | public — runs `SELECT 1`; returns 503 if PostgreSQL is unreachable |
| POST | `/api/analytics/visit` | public |
| GET | `/api/analytics` | admin |

## Security

- Passwords hashed with bcrypt (passlib).
- JWT (HS256) via OAuth2PasswordBearer; admin-only routes are guarded by a role check (`app/core/dependencies.py`).
- `/api/auth/login` is rate-limited (slowapi) against brute-force attempts.
- CORS allows only the origins listed in `FRONTEND_URL` (comma-separated, e.g. `https://<user>.github.io,http://localhost:5500`) — never `*` — since the API is authenticated.
- All exceptions are caught centrally (`app/main.py`) so stack traces and internals are never returned to the client.

## Database: Supabase Postgres

1. Create a project at [supabase.com](https://supabase.com).
2. Apply the schema: `psql "$SUPABASE_DB_URL" -f ../supabase/migrations/0001_init.sql` (or `supabase db push` if you're using the Supabase CLI and have linked the project).
3. Grab the **pooled** connection string (Project Settings → Database → Connection string → "Transaction" mode, port 6543) for `DATABASE_URL` — see `.env.example` for why the pooled port matters on serverless.
4. **Migrating existing data from another Postgres instance** (e.g. if you were previously on Azure Database for PostgreSQL via Render): `pg_dump --no-owner --no-privileges --format=custom "$OLD_DATABASE_URL" > backup.dump`, then restore with `pg_restore --no-owner --no-privileges -d "$SUPABASE_DIRECT_DB_URL" backup.dump` against Supabase's **direct** connection (port 5432, not the pooler — `pg_restore` needs a session-level connection). Run this once, before pointing the app at Supabase.

## Deploying to Vercel

This service is deployed on **Vercel** as a Python serverless project (Supabase hosts the database only — it has no facility to run a persistent FastAPI process). `backend/vercel.json` builds `api/index.py`, a thin wrapper that re-exports the existing `app.main.app` ASGI app unchanged, and rewrites every path to it.

1. Push this repo to GitHub.
2. In Vercel, import the repo as a new project with **Root Directory = `backend`**. Vercel detects `vercel.json` and builds `api/index.py` with the `@vercel/python` runtime.
3. Set the environment variables in that Vercel project's dashboard (never commit them): `DATABASE_URL` (Supabase's pooled connection string, see above), `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_URL` (the frontend's Vercel origin, plus `http://localhost:5500` for local development, comma-separated), `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `BACKEND_URL` (this backend's own Vercel URL, used to build OAuth callback URLs), and the Google/GitHub OAuth client vars.
4. Update the redirect/callback URIs registered in the Google Cloud Console and GitHub OAuth App settings to `{BACKEND_URL}/api/auth/google/callback` and `{BACKEND_URL}/api/auth/github/callback` using the new Vercel URL.

**Known limitation:** `/api/auth/login`'s rate limiting (`slowapi`, `app/core/rate_limit.py`) uses in-memory storage. On Vercel, each serverless instance has its own memory, so the limit is per-instance rather than global, and resets on cold start. For this portfolio's traffic that's an acceptable tradeoff; if it ever needs to be airtight, swap the limiter's storage backend for Redis (e.g. Upstash) or a Postgres-backed counter instead.

## Frontend integration

The frontend calls this API through a single `API_BASE_URL` constant (`frontend/js/config.js`) — never hardcoded inline. Point it at `http://localhost:8000` in development and this backend's Vercel URL in production.
