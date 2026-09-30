# Portfolio API

FastAPI backend for the portfolio's contact form and admin login. Uses SQLAlchemy + Alembic against PostgreSQL, and JWT auth for a single admin account defined via environment variables.

## Architecture

```
GitHub Pages (static frontend)
      ↓
FastAPI REST API  (this service)
      ↓
SQLAlchemy
      ↓
PostgreSQL
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs` and `http://localhost:8000/redoc`.

## Endpoints

- `POST /api/auth/login` — admin login, returns a JWT
- `POST /api/contact` — public, submit a contact form message
- `GET /api/contact` — admin only, list messages
- `GET /api/contact/{id}` — admin only, fetch one (marks it read)
- `DELETE /api/contact/{id}` — admin only, delete a message
- `GET /health` — health check

## Deploying to Render

This service is deployed on **Render**. Do not use Railway.

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from `backend/render.yaml` (or create the Web Service manually, with root directory `backend`).
3. Build command: `pip install -r requirements.txt && alembic upgrade head`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add a managed PostgreSQL instance on Render (or link the one in `render.yaml`) and let Render inject `DATABASE_URL`.
6. Set the remaining environment variables in the Render dashboard (never commit them):
   - `SECRET_KEY`
   - `ALGORITHM`
   - `ACCESS_TOKEN_EXPIRE_MINUTES`
   - `FRONTEND_URL` — your GitHub Pages origin, e.g. `https://your-username.github.io`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`

Render supplies `$PORT` at runtime; the start command must bind to it (already does above) rather than a hardcoded port.

## Frontend integration

Point the static frontend at the deployed API via an `API_BASE_URL` constant, e.g.:

```js
const API_BASE_URL = "https://your-backend.onrender.com";
```

Never hardcode `localhost` in the production frontend build.
