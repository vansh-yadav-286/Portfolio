# Portfolio API (backend)

FastAPI backend for the portfolio: projects, certificates, workshops/hackathons, experience, and a contact form, with Google/GitHub OAuth and role-based admin access. **No database.** Content lives in JSON files (`app/data/`); auth is a signed, stateless session cookie derived from the OAuth provider's verified identity - there is no user table, no password, no Supabase, no SQLAlchemy, no Alembic.

## Architecture

```
frontend/  (HTML/CSS/JS)
    ↓ REST (fetch, credentials: 'include')
backend/app/routes      ← HTTP layer, request/response shapes
    ↓
backend/app/schemas     ← Pydantic validation
    ↓
backend/app/services    ← business logic
    ↓
backend/app/data/*.json  (content)  /  Google & GitHub OAuth (identity)
```

```
app/
├── main.py            # app wiring: CORS, exception handlers, routers
├── core/
│   ├── config.py       # Settings (env vars)
│   ├── security.py     # session cookie sign/verify, OAuth state sign/verify
│   ├── dependencies.py # get_current_user / get_current_admin / verify_csrf
│   └── rate_limit.py   # slowapi limiter (login, contact form)
├── routes/             # one file per resource, thin HTTP layer
├── services/           # business logic, called by routes
├── schemas/            # Pydantic request/response models
├── data/                # projects.json, certificates.json, experiences.json,
│                        # hackathons.json + store.py's read/write helpers
└── utils/helpers.py    # success_response(), api_error()
tests/                  # pytest, one file per resource — 63 tests
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SESSION_SECRET, ADMIN_EMAIL, OAuth creds, SMTP creds

uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs` and `http://localhost:8000/redoc`.

There is no admin account to seed. Whichever Google or GitHub account authenticates with the exact, provider-verified email set in `ADMIN_EMAIL` is granted the admin role at login time - nothing is created, stored, or needs resetting.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

CI runs the same suite on every push and pull request that touches `backend/` (see `.github/workflows/backend-tests.yml`).

Each test gets its own throwaway copy of `app/data/*.json` (`tests/conftest.py`'s `isolated_data_dir` fixture), independent of your real content files. OAuth provider calls (Google/GitHub token exchange and profile fetch) are mocked - no test ever makes a real network call to either provider.

## API

All responses use a consistent envelope:

```json
{ "success": true, "message": "...", "data": { ... } }
{ "success": false, "message": "..." }
```

| Method | Path | Auth |
|---|---|---|
| GET | `/api/auth/google/login`, `/api/auth/github/login` | public (rate-limited: 10/min) |
| GET | `/api/auth/google/callback`, `/api/auth/github/callback` | public (completes the OAuth flow) |
| GET | `/api/auth/me` | any authenticated session |
| POST | `/api/auth/logout` | any authenticated session (+ CSRF header) |
| GET | `/api/projects`, `/api/projects/{id}` | public |
| POST/PUT/DELETE | `/api/projects[/{id}]` | admin + CSRF header |
| GET | `/api/certificates`, `/api/certificates/{id}` | public |
| POST/PUT/DELETE | `/api/certificates[/{id}]` | admin + CSRF header |
| GET | `/api/experiences`, `/api/experiences/{id}` | public |
| POST/PUT/DELETE | `/api/experiences[/{id}]` | admin + CSRF header |
| GET | `/api/hackathons` | public (visible items only) |
| GET | `/api/hackathons/manage` | admin (all items, including hidden) |
| POST/PUT/DELETE | `/api/hackathons[/{id}]` | admin + CSRF header |
| POST | `/api/contact` | public (rate-limited: 5/min) - forwards by email, nothing is stored |
| GET | `/health` | public - plain liveness check, no database to probe |

## Security

- Google/GitHub OAuth only. A login is accepted only if the provider reports the email as verified - an unverified email is always rejected, never trusted on a string match.
- Sessions are a signed (HS256), stateless JWT delivered as an **HttpOnly** cookie - never readable by page scripts, never put in `localStorage`/`sessionStorage`. `role` ("admin" vs "user") is decided once, at login, by comparing the verified email against `ADMIN_EMAIL` (case-insensitive) - it is baked into the token, not re-derived from anywhere.
- CSRF protection on every mutating admin request (`core/dependencies.py::verify_csrf`): the frontend must echo a token from `GET /api/auth/me` back as `X-CSRF-Token`. This is required specifically because the session cookie is sent cross-site (`SameSite=None` in production, since Vercel and Render are different origins), which alone gives no CSRF protection.
- `/api/auth/*/login` and `/api/contact` are rate-limited (slowapi) against abuse.
- CORS allows only the origins listed in `FRONTEND_URL` (comma-separated, e.g. `https://<project>.vercel.app,http://localhost:5500`) — never `*` — required for the cross-site cookie to be sent at all, not just good practice.
- All exceptions are caught centrally (`app/main.py`) so stack traces and internals are never returned to the client.
- No database, so no SQL injection surface for this API's own queries; content writes go through `app/data/store.py`'s atomic JSON read/write.

## Content storage - and its one real limitation

`app/data/{projects,certificates,experiences,hackathons}.json` are the content. See [`app/data/README.md`](app/data/README.md) for the exact shape of each file.

**Writes made through the admin dashboard are not durable on Render.** Render's filesystem resets on every redeploy (and isn't guaranteed to survive a plain restart either, depending on plan). An edit made through the admin UI will be silently lost the next time the service redeploys unless the updated JSON file is also committed back into the repo. Treat the admin editor as a convenience for drafting content you'll immediately commit, not as a live CMS.

## Deploying to Render

This service is deployed on **Render**, as a normal persistent web service — the in-memory rate limiter and the OAuth flow both assume one long-lived process, which serverless platforms don't give you (each instance has its own memory, with no state shared between them). `render.yaml` at the repo root is a ready-to-use Blueprint - a single web service, no database.

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo's `render.yaml`.
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set the environment variables in the Render dashboard (never commit them): `SESSION_SECRET`, `SESSION_MAX_AGE_MINUTES`, `FRONTEND_URL` (the frontend's Vercel origin, plus `http://localhost:5500` for local development, comma-separated), `ADMIN_EMAIL`, `BACKEND_URL` (this service's own Render URL, used to build OAuth callback URLs), the Google/GitHub OAuth client vars, and the SMTP vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `CONTACT_EMAIL_TO`, `CONTACT_EMAIL_FROM`).
6. Update the redirect/callback URIs registered in the Google Cloud Console and GitHub OAuth App settings to `{BACKEND_URL}/api/auth/google/callback` and `{BACKEND_URL}/api/auth/github/callback` using the real Render URL.

Render supplies `$PORT` at runtime; the start command binds to it rather than a hardcoded port.

## Frontend integration

The frontend calls this API through a single `API_BASE_URL` constant (`frontend/js/config.js`) — never hardcoded inline. Point it at `http://localhost:8000` in development and this backend's Render URL in production. Every authenticated `fetch()` must pass `credentials: 'include'` so the session cookie is sent; mutating admin requests must also attach `X-CSRF-Token` (from `GET /api/auth/me`'s response).
