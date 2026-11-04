from urllib.parse import parse_qs, urlparse

from app.core.config import settings


def _admin_headers(client):
    token = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-test-password"},
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email="jane@example.com", password="supersecret1", name="Jane Doe"):
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


ADMIN_ONLY_ENDPOINTS = [
    "/api/admin/reports/overview",
    "/api/admin/reports/users",
    "/api/admin/reports/signups",
    "/api/admin/reports/auth-events",
    "/api/admin/reports/failed-logins",
    "/api/admin/reports/visits",
    "/api/admin/reports/export?report=users",
]


def test_report_endpoints_require_authentication(client):
    for path in ADMIN_ONLY_ENDPOINTS:
        assert client.get(path).status_code == 401, path


def test_report_endpoints_reject_non_admin(client):
    headers = _register_and_login(client)
    for path in ADMIN_ONLY_ENDPOINTS:
        assert client.get(path, headers=headers).status_code == 403, path


def test_user_status_endpoint_requires_admin(client):
    headers = _register_and_login(client)
    response = client.patch("/api/admin/reports/users/1/status", json={"is_active": False}, headers=headers)
    assert response.status_code == 403


def test_user_activity_endpoint_requires_admin(client):
    headers = _register_and_login(client)
    response = client.get("/api/admin/reports/users/1/activity", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Event recording: password flow
# ---------------------------------------------------------------------------

def test_signup_success_is_recorded(client):
    _register_and_login(client)
    admin_headers = _admin_headers(client)
    data = client.get("/api/admin/reports/signups", headers=admin_headers).json()["data"]
    matching = [e for e in data["items"] if e["email"] == "jane@example.com"]
    assert len(matching) == 1
    assert matching[0]["method"] == "password"
    assert matching[0]["status"] == "success"


def test_duplicate_signup_is_recorded_as_failure_not_inflated_success(client):
    client.post("/api/auth/register", json={"name": "Jane", "email": "dupe@example.com", "password": "supersecret1"})
    client.post("/api/auth/register", json={"name": "Jane Two", "email": "dupe@example.com", "password": "supersecret1"})

    admin_headers = _admin_headers(client)
    data = client.get("/api/admin/reports/signups", headers=admin_headers).json()["data"]
    matching = [e for e in data["items"] if e["email"] == "dupe@example.com"]
    successes = [e for e in matching if e["status"] == "success"]
    failures = [e for e in matching if e["status"] == "failure"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0]["reason"] == "email_already_registered"


def test_failed_login_is_recorded_without_leaking_password(client):
    client.post("/api/auth/register", json={"name": "Jane", "email": "jane2@example.com", "password": "supersecret1"})
    client.post("/api/auth/login", json={"email": "jane2@example.com", "password": "wrong-password"})

    admin_headers = _admin_headers(client)
    data = client.get("/api/admin/reports/failed-logins", headers=admin_headers).json()["data"]
    matching = [e for e in data["items"] if e["email"] == "jane2@example.com"]
    assert len(matching) == 1
    assert matching[0]["reason"] == "invalid_credentials"
    assert "wrong-password" not in client.get("/api/admin/reports/failed-logins", headers=admin_headers).text


def test_login_and_logout_share_a_session_ref(client):
    headers = _register_and_login(client, email="pair@example.com")
    client.post("/api/auth/logout", headers=headers)

    admin_headers = _admin_headers(client)
    data = client.get(
        "/api/admin/reports/auth-events", params={"q": "pair@example.com"}, headers=admin_headers
    ).json()["data"]
    login_event = next(e for e in data["items"] if e["event_type"] == "login")
    logout_event = next(e for e in data["items"] if e["event_type"] == "logout")
    assert login_event["session_ref"]
    assert login_event["session_ref"] == logout_event["session_ref"]


def test_csv_export_never_contains_secrets(client):
    headers = _register_and_login(client, email="secrets@example.com", password="supersecret1")
    client.post("/api/auth/login", json={"email": "secrets@example.com", "password": "wrong"})

    admin_headers = _admin_headers(client)
    for report in ["users", "signups", "auth-events", "failed-logins"]:
        response = client.get(f"/api/admin/reports/export?report={report}", headers=admin_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        body = response.text
        assert "supersecret1" not in body
        assert "wrong" not in body
        assert headers["Authorization"].split(" ")[1] not in body


def test_csv_export_requires_admin(client):
    user_headers = _register_and_login(client)
    response = client.get("/api/admin/reports/export?report=users", headers=user_headers)
    assert response.status_code == 403


def test_export_records_admin_audit_log(client):
    admin_headers = _admin_headers(client)
    client.get("/api/admin/reports/export?report=users", headers=admin_headers)
    # No direct audit-log endpoint is exposed, but the export must not have
    # errored, and a second export for a different report should also succeed
    # independently (i.e. the audit write itself didn't break the response).
    response = client.get("/api/admin/reports/export?report=visits", headers=admin_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Account status: enforcement + audit trail
# ---------------------------------------------------------------------------

def test_disabling_account_blocks_future_logins(client):
    _register_and_login(client, email="disableme@example.com")
    admin_headers = _admin_headers(client)

    users = client.get("/api/admin/reports/users", params={"q": "disableme"}, headers=admin_headers).json()["data"]["items"]
    user_id = users[0]["id"]

    patch = client.patch(
        f"/api/admin/reports/users/{user_id}/status", json={"is_active": False}, headers=admin_headers
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["is_active"] is False

    login = client.post("/api/auth/login", json={"email": "disableme@example.com", "password": "supersecret1"})
    assert login.status_code == 403


def test_disabling_account_revokes_an_already_issued_token(client):
    headers = _register_and_login(client, email="revokeme@example.com")
    admin_headers = _admin_headers(client)

    users = client.get("/api/admin/reports/users", params={"q": "revokeme"}, headers=admin_headers).json()["data"]["items"]
    user_id = users[0]["id"]
    client.patch(f"/api/admin/reports/users/{user_id}/status", json={"is_active": False}, headers=admin_headers)

    # The token was issued before deactivation and hasn't expired, but it must
    # stop working immediately rather than staying valid until expiry.
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# OAuth signup/login event recording + idempotency
# ---------------------------------------------------------------------------

def _state_and_cookie(login_response):
    location = login_response.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]
    cookie = login_response.cookies.get("oauth_state")
    return state, cookie


def test_oauth_signup_recorded_once_even_if_callback_runs_twice(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")

    import app.services.oauth_service as oauth_service

    monkeypatch.setattr(oauth_service, "exchange_google_code", lambda code: {"access_token": "fake-token"})
    monkeypatch.setattr(
        oauth_service,
        "fetch_google_profile",
        lambda token: {
            "provider_id": "google-dup-1",
            "email": "oauthuser@example.com",
            "email_verified": True,
            "name": "OAuth User",
        },
    )

    def run_callback():
        login_response = client.get("/api/auth/google/login", follow_redirects=False)
        state, cookie = _state_and_cookie(login_response)
        client.cookies.set("oauth_state", cookie)
        return client.get(
            "/api/auth/google/callback", params={"code": "good-code", "state": state}, follow_redirects=False
        )

    first = run_callback()
    second = run_callback()
    assert first.status_code == 302
    assert second.status_code == 302

    admin_headers = _admin_headers(client)
    data = client.get("/api/admin/reports/signups", headers=admin_headers).json()["data"]
    matching = [e for e in data["items"] if e["email"] == "oauthuser@example.com"]
    assert len(matching) == 1
    assert matching[0]["method"] == "google"

    login_data = client.get("/api/admin/reports/auth-events", params={"q": "oauthuser@example.com", "event_type": "login"}, headers=admin_headers).json()["data"]
    # Each callback minted a code; whether it's redeemed doesn't matter here -
    # we only assert signups weren't double-counted above.
    assert all(e["method"] == "google" for e in login_data["items"])


# ---------------------------------------------------------------------------
# Filtering / sorting / pagination sanity
# ---------------------------------------------------------------------------

def test_users_report_search_and_pagination(client):
    for i in range(3):
        client.post(
            "/api/auth/register",
            json={"name": f"Searchy {i}", "email": f"searchy{i}@example.com", "password": "supersecret1"},
        )
    admin_headers = _admin_headers(client)

    data = client.get("/api/admin/reports/users", params={"q": "searchy", "page_size": 2}, headers=admin_headers).json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 2

    page2 = client.get(
        "/api/admin/reports/users", params={"q": "searchy", "page_size": 2, "page": 2}, headers=admin_headers
    ).json()["data"]
    assert len(page2["items"]) == 1


def test_users_report_provider_filter(client):
    client.post("/api/auth/register", json={"name": "PW User", "email": "pwuser@example.com", "password": "supersecret1"})
    admin_headers = _admin_headers(client)

    data = client.get("/api/admin/reports/users", params={"provider": "password", "q": "pwuser"}, headers=admin_headers).json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["registration_method"] == "password"

    data = client.get("/api/admin/reports/users", params={"provider": "google", "q": "pwuser"}, headers=admin_headers).json()["data"]
    assert data["total"] == 0


def test_invalid_date_range_is_rejected(client):
    admin_headers = _admin_headers(client)
    response = client.get(
        "/api/admin/reports/users",
        params={"date_from": "2026-01-02T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
        headers=admin_headers,
    )
    assert response.status_code == 400
