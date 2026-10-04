import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "admin-test-password")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5500")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.database import get_db
from app.main import app
from app.models import *  # noqa: F401,F403 - register all models on Base.metadata

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    from app.core.rate_limit import limiter

    limiter.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-test-password"},
    )
    return response.json()["data"]["access_token"]
