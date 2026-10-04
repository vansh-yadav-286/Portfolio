import pytest


def _admin_headers(client):
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-test-password"},
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _register_user(client):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "jane@example.com", "password": "supersecret1"},
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


PROJECT = {"title": "Demo", "description": "A project", "technologies": "Python"}


def test_non_admin_cannot_create_project(client):
    headers = _register_user(client)
    response = client.post("/api/projects", json=PROJECT, headers=headers)
    assert response.status_code == 403


def test_non_admin_cannot_read_analytics(client):
    headers = _register_user(client)
    assert client.get("/api/analytics", headers=headers).status_code == 403


def test_admin_can_read_analytics(client):
    response = client.get("/api/analytics", headers=_admin_headers(client))
    assert response.status_code == 200
    assert response.json()["data"]["total_visitors"] == 0


def test_visit_is_recorded_with_hashed_ip(client):
    response = client.post(
        "/api/analytics/visit",
        json={"session_id": "abc", "page": "/"},
        headers={"X-Forwarded-For": "203.0.113.7"},
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "bad_url",
    ["javascript:alert(1)", "data:text/html,<script>x</script>", "//evil.example.com/x"],
)
def test_project_rejects_unsafe_urls(client, bad_url):
    response = client.post(
        "/api/projects", json={**PROJECT, "live_url": bad_url}, headers=_admin_headers(client)
    )
    assert response.status_code == 422


def test_project_accepts_http_and_relative_urls(client):
    response = client.post(
        "/api/projects",
        json={**PROJECT, "live_url": "https://example.com", "image_url": "assets/x.jpg"},
        headers=_admin_headers(client),
    )
    assert response.status_code == 201


def test_empty_url_is_stored_as_null(client):
    response = client.post(
        "/api/projects", json={**PROJECT, "github_url": "  "}, headers=_admin_headers(client)
    )
    assert response.status_code == 201
    assert response.json()["data"]["github_url"] is None


def test_contact_endpoint_is_rate_limited(client):
    payload = {"name": "Visitor", "email": "v@example.com", "message": "hi"}
    statuses = [client.post("/api/contact", json=payload).status_code for _ in range(6)]
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


def test_visit_endpoint_is_rate_limited(client):
    payload = {"session_id": "abc", "page": "/"}
    statuses = [client.post("/api/analytics/visit", json=payload).status_code for _ in range(61)]
    assert statuses[-1] == 429
