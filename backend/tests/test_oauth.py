from urllib.parse import parse_qs, urlparse

from app.core.config import settings


def _configure_google(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-google-client-id")
    monkeypatch.setattr(settings, "google_client_secret", "test-google-client-secret")


def _configure_github(monkeypatch):
    monkeypatch.setattr(settings, "github_client_id", "test-github-client-id")
    monkeypatch.setattr(settings, "github_client_secret", "test-github-client-secret")


def _state_and_cookie(login_response):
    location = login_response.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]
    cookie = login_response.cookies.get("oauth_state")
    return state, cookie


def _redirect_query(response):
    return parse_qs(urlparse(response.headers["location"]).query)


def test_google_login_not_configured_returns_503(client, monkeypatch):
    # Explicitly blank, not just relying on ambient env - a developer's local
    # backend/.env (never read in CI) could otherwise make this test flaky.
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 503


def test_github_login_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "github_client_id", "")
    monkeypatch.setattr(settings, "github_client_secret", "")
    response = client.get("/api/auth/github/login", follow_redirects=False)
    assert response.status_code == 503


def test_google_login_redirects_to_google_with_state_cookie(client, monkeypatch):
    _configure_google(monkeypatch)
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["location"]
    assert response.cookies.get("oauth_state")


def test_google_login_ignores_untrusted_redirect_target(client, monkeypatch):
    _configure_google(monkeypatch)
    response = client.get(
        "/api/auth/google/login",
        params={"redirect": "https://evil.example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    # The signed state carries the redirect target; it must have fallen back
    # to an allowed frontend origin rather than trusting the attacker's URL.
    import app.core.security as security_module

    state, _ = _state_and_cookie(response)
    payload = security_module.verify_oauth_state(state, max_age_seconds=600)
    assert payload["redirect"] == "http://localhost:5500"


def test_google_callback_without_state_shows_error(client, monkeypatch):
    _configure_google(monkeypatch)
    response = client.get("/api/auth/google/callback", params={"code": "abc"}, follow_redirects=False)
    assert response.status_code == 302
    assert "oauth_error" in _redirect_query(response)


def test_google_callback_rejects_mismatched_state(client, monkeypatch):
    _configure_google(monkeypatch)
    login_response = client.get("/api/auth/google/login", follow_redirects=False)
    _, cookie = _state_and_cookie(login_response)
    client.cookies.set("oauth_state", cookie)

    response = client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": "forged-state-value"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "oauth_error" in _redirect_query(response)


def test_google_callback_denied_by_user(client, monkeypatch):
    _configure_google(monkeypatch)
    response = client.get(
        "/api/auth/google/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "oauth_error" in _redirect_query(response)


def _run_google_oauth(client, monkeypatch, *, email, provider_id, email_verified=True, name="Someone"):
    """Drives login -> callback for a stubbed Google identity (the real Google
    token exchange / profile fetch are mocked - nothing here talks to Google)
    and returns the callback's redirect response."""
    _configure_google(monkeypatch)
    import app.services.oauth_service as oauth_service

    monkeypatch.setattr(oauth_service, "exchange_google_code", lambda code: {"access_token": "fake-token"})
    monkeypatch.setattr(
        oauth_service,
        "fetch_google_profile",
        lambda token: {
            "provider_id": provider_id,
            "email": email,
            "email_verified": email_verified,
            "name": name,
        },
    )

    login_response = client.get("/api/auth/google/login", follow_redirects=False)
    state, cookie = _state_and_cookie(login_response)
    client.cookies.set("oauth_state", cookie)

    return client.get(
        "/api/auth/google/callback",
        params={"code": "good-code", "state": state},
        follow_redirects=False,
    )


def test_oauth_callback_never_puts_identity_in_the_redirect(client, monkeypatch):
    """The callback redirect must carry no email, token, or code - identity
    lives only in the HttpOnly session cookie set on this same response."""
    response = _run_google_oauth(
        client, monkeypatch, email="newperson@example.com", provider_id="google-123"
    )
    assert response.status_code == 302
    query = _redirect_query(response)
    assert query.get("oauth") == ["success"]
    assert "email" not in query
    assert "token" not in query
    assert "code" not in query
    assert response.cookies.get("session")


def test_oauth_establishes_a_real_session_for_new_user(client, monkeypatch):
    response = _run_google_oauth(
        client, monkeypatch, email="newperson@example.com", provider_id="google-123", name="New Person"
    )
    assert response.cookies.get("session")

    # The cookie set on the callback must actually authorize /me on this client.
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    data = me.json()["data"]
    assert data["email"] == "newperson@example.com"
    assert data["role"] == "user"
    assert data["provider"] == "google"


def test_oauth_grants_admin_role_only_for_admin_email(client, monkeypatch):
    response = _run_google_oauth(
        client, monkeypatch, email="admin@example.com", provider_id="google-admin"
    )
    assert response.cookies.get("session")
    me = client.get("/api/auth/me")
    assert me.json()["data"]["role"] == "admin"


def test_oauth_admin_email_match_is_case_insensitive(client, monkeypatch):
    response = _run_google_oauth(
        client, monkeypatch, email="Admin@Example.com", provider_id="google-admin-case"
    )
    assert response.cookies.get("session")
    me = client.get("/api/auth/me")
    assert me.json()["data"]["role"] == "admin"


def test_oauth_rejects_unverified_email(client, monkeypatch):
    response = _run_google_oauth(
        client,
        monkeypatch,
        email="unverified@example.com",
        provider_id="google-unverified",
        email_verified=False,
    )
    assert response.status_code == 302
    assert "oauth_error" in _redirect_query(response)
    assert not response.cookies.get("session")


def test_unauthenticated_request_cannot_reach_protected_endpoint(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_github_callback_handles_private_email_and_establishes_session(client, monkeypatch):
    _configure_github(monkeypatch)
    import app.services.oauth_service as oauth_service

    monkeypatch.setattr(oauth_service, "exchange_github_code", lambda code: {"access_token": "fake-token"})
    monkeypatch.setattr(
        oauth_service,
        "fetch_github_profile",
        lambda token: {
            "provider_id": "gh-1",
            "email": "private@example.com",
            "email_verified": True,
            "name": "GitHub User",
        },
    )

    login_response = client.get("/api/auth/github/login", follow_redirects=False)
    state, cookie = _state_and_cookie(login_response)
    client.cookies.set("oauth_state", cookie)

    response = client.get(
        "/api/auth/github/callback",
        params={"code": "good-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.cookies.get("session")

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "private@example.com"
    assert me.json()["data"]["provider"] == "github"
