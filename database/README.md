# database/

PostgreSQL schema, migrations, seed data and documentation for the portfolio. No application code lives here.

```
database/
├── migrations/
│   └── alembic/          # Alembic environment + versioned migrations
├── schemas/
│   └── schema.sql         # Reference DDL (documentation; Alembic is the source of truth)
├── seeds/
│   └── seed.sql            # Initial projects + certificates data
├── docs/
│   └── database.md        # Setup, migration and seeding instructions
└── alembic.ini
```

SQLAlchemy models are **not** duplicated here — they live in `backend/app/models/`, since they're part of the backend application layer. This folder only holds the database's own artifacts: schema, migrations, seeds and docs.

See [`docs/database.md`](docs/database.md) for setup instructions.
