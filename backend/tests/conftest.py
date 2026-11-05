import os

os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5500")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import SESSION_COOKIE
from app.core.security import create_session_token
from app.data import store
from app.main import app

SEED_FILES = ["projects", "certificates", "experiences", "hackathons"]


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    # Each test gets its own throwaway copy of app/data/*.json, so tests never
    # touch (or depend on) the real content files and don't leak state between
    # each other - the closest equivalent to the old per-test SQLite database.
    for name in SEED_FILES:
        shutil.copy(store.DATA_DIR / f"{name}.json", tmp_path / f"{name}.json")
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    yield tmp_path


@pytest.fixture()
def client():
    from app.core.rate_limit import limiter

    limiter.reset()
    with TestClient(app) as c:
        yield c


def _login_as(client: TestClient, email: str, role: str, name: str = "Test User", provider: str = "google"):
    token, csrf = create_session_token(email=email, name=name, role=role, provider=provider)
    client.cookies.set(SESSION_COOKIE, token)
    return csrf


@pytest.fixture()
def admin_csrf(client):
    """Logs `client` in as the admin (matching ADMIN_EMAIL) and returns the CSRF
    token to attach as X-CSRF-Token on mutating requests - mirrors a real
    frontend, which gets this value from GET /api/auth/me after OAuth login.
    """
    return _login_as(client, email="admin@example.com", role="admin")


@pytest.fixture()
def user_csrf(client):
    return _login_as(client, email="visitor@example.com", role="user")


def write_items(tmp_path, name: str, items: list[dict]) -> None:
    with (tmp_path / f"{name}.json").open("w") as f:
        json.dump(items, f, default=str)
