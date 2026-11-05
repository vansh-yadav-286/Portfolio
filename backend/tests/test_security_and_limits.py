import pytest

PROJECT = {"title": "Demo", "description": "A project", "technologies": "Python"}


def _configure_smtp(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "contact_email_to", "owner@example.com")
    monkeypatch.setattr(settings, "contact_email_from", "noreply@example.com")
    monkeypatch.setattr("app.services.contact_service.send_contact_email", lambda *a: None)


@pytest.mark.parametrize(
    "bad_url",
    ["javascript:alert(1)", "data:text/html,<script>x</script>", "//evil.example.com/x"],
)
def test_project_rejects_unsafe_urls(client, admin_csrf, bad_url):
    response = client.post(
        "/api/projects",
        json={**PROJECT, "live_url": bad_url},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 422


def test_project_accepts_http_and_relative_urls(client, admin_csrf):
    response = client.post(
        "/api/projects",
        json={**PROJECT, "live_url": "https://example.com", "image_url": "assets/x.jpg"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 201


def test_empty_url_is_stored_as_null(client, admin_csrf):
    response = client.post(
        "/api/projects",
        json={**PROJECT, "github_url": "  "},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 201
    assert response.json()["data"]["github_url"] is None


def test_contact_endpoint_is_rate_limited(client, monkeypatch):
    _configure_smtp(monkeypatch)
    payload = {"name": "Visitor", "email": "v@example.com", "message": "hi"}
    statuses = [client.post("/api/contact", json=payload).status_code for _ in range(6)]
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


def test_google_login_is_rate_limited(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "google_client_id", "id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    statuses = [
        client.get("/api/auth/google/login", follow_redirects=False).status_code for _ in range(11)
    ]
    assert statuses[:10] == [302] * 10
    assert statuses[10] == 429
