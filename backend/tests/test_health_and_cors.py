from app.core.config import Settings


def make_settings(frontend_url: str) -> Settings:
    return Settings(
        database_url="sqlite:///./test.db",
        secret_key="test-secret-key",
        admin_email="admin@example.com",
        admin_password="admin-test-password",
        frontend_url=frontend_url,
    )


def test_health_runs_a_real_database_query(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok", "database": "connected"}


def test_health_reports_503_when_database_is_unreachable(client, monkeypatch):
    def broken_connection():
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.main.check_database_connection", broken_connection)

    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"]["database"] == "unreachable"
    # The internal error message must not leak to the client.
    assert "connection refused" not in response.text


def test_frontend_origins_split_and_trimmed():
    settings = make_settings(" https://user.github.io/ , http://localhost:5500 ")

    assert settings.frontend_origins == ["https://user.github.io", "http://localhost:5500"]


def test_cors_allows_configured_origin_only(client):
    allowed = client.options(
        "/api/projects",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5500"

    denied = client.options(
        "/api/projects",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.headers.get("access-control-allow-origin") is None
