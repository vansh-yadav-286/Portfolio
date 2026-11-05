from app.core.config import Settings


def make_settings(frontend_url: str) -> Settings:
    return Settings(
        session_secret="test-secret",
        admin_email="admin@example.com",
        frontend_url=frontend_url,
    )


def test_health_is_a_simple_liveness_check(client):
    # No database to check any more - this only proves the process is up.
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok"}


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
