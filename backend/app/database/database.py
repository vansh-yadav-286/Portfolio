from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.database.base import Base

# NullPool: each serverless invocation is a separate, short-lived process, so
# there's no benefit to an in-process connection pool - and against Supabase's
# pooled connection string (Supavisor/PgBouncer in transaction mode), holding
# a persistent pool on top of a pooler just doubles the pooling. prepare_threshold=None
# disables psycopg's server-side prepared statements, which PgBouncer's
# transaction pooling mode doesn't support reliably across requests.
engine = create_engine(
    settings.sqlalchemy_database_url,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

__all__ = ["engine", "SessionLocal", "Base", "check_database_connection"]


def check_database_connection() -> None:
    # A real round trip to the server. Raises if the database is unreachable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
