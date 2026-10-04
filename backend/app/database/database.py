from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.base import Base

engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

__all__ = ["engine", "SessionLocal", "Base"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
