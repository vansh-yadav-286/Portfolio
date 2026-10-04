# Database

PostgreSQL, managed through SQLAlchemy models (in `backend/app/models/`) and versioned with Alembic migrations (in this folder).

## Tables

| Table | Purpose |
|---|---|
| `users` | Accounts for the auth system. `role` is `admin` or `user`; only `admin` can manage content. |
| `projects` | Portfolio projects shown on the public site and managed from the admin dashboard. |
| `certificates` | Certifications shown on the public site. |
| `contact_messages` | Messages submitted through the public contact form. `status` tracks moderation state. |
| `visitors` | Anonymous page-visit events for analytics (no PII beyond a hashed IP). |

See [`schemas/schema.sql`](../schemas/schema.sql) for the full column-level reference schema (documentation only — the real source of truth is the Alembic migrations).

## 1. Install PostgreSQL

Use a local install, Docker, or any managed Postgres provider (Render's managed Postgres is what production uses). Create a database and user, e.g.:

```sql
CREATE DATABASE portfolio_db;
CREATE USER portfolio_user WITH PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE portfolio_db TO portfolio_user;
```

## 2. Configure DATABASE_URL

In `backend/.env` (copied from `backend/.env.example`):

```
DATABASE_URL=postgresql+psycopg://portfolio_user:change-me@localhost:5432/portfolio_db
```

## 3. Run migrations

Alembic is configured to run from this `database/` directory and import the SQLAlchemy models from `backend/app/`:

```bash
cd database
python -m venv .venv && source .venv/bin/activate   # or reuse backend/.venv
pip install -r ../backend/requirements.txt
alembic upgrade head
```

To create a new migration after changing a model in `backend/app/models/`:

```bash
cd database
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## 4. Seed data

Seed data mirrors the portfolio's original hardcoded projects and certificates:

```bash
psql "$DATABASE_URL" -f seeds/seed.sql
```

The admin account is **not** seeded via SQL — it is created automatically the first time the backend starts, from the `ADMIN_EMAIL` / `ADMIN_PASSWORD` environment variables, so no password hash is ever committed to the repository.

## 5. Start the backend

See [`backend/README.md`](../backend/README.md).
