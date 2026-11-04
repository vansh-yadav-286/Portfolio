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


def test_google_login_not_configured_returns_503(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 503


def test_github_login_not_configured_returns_503(client):
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


def _run_google_oauth_success(client, monkeypatch, *, email, provider_id, email_verified=True, name="Someone"):
    """Drives login -> callback for a stubbed Google identity and returns the
    one-time code from the callback's redirect, without assuming it's valid."""
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

    callback_response = client.get(
        "/api/auth/google/callback",
        params={"code": "good-code", "state": state},
        follow_redirects=False,
    )
    return callback_response


def test_oauth_callback_never_puts_identity_in_the_redirect(client, monkeypatch):
    """The whole point of the exchange flow: the callback redirect must not
    contain the user's email, an access token, or anything else a page could
    mistake for proof of identity - only an opaque one-time code."""
    response = _run_google_oauth_success(
        client, monkeypatch, email="newperson@example.com", provider_id="google-123"
    )
    assert response.status_code == 302
    query = _redirect_query(response)
    assert query.get("oauth") == ["success"]
    assert "email" not in query
    assert "token" not in query
    assert "access_token" not in query
    code = query["code"][0]
    assert code and code != "good-code"


def test_oauth_exchange_establishes_a_real_session_for_new_user(client, monkeypatch):
    response = _run_google_oauth_success(
        client, monkeypatch, email="newperson@example.com", provider_id="google-123", name="New Person"
    )
    code = _redirect_query(response)["code"][0]

    exchange = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert exchange.status_code == 200
    body = exchange.json()
    assert body["success"] is True
    token = body["data"]["access_token"]
    assert token

    # The access token must actually authorize calls to a protected endpoint -
    # this is the real proof of a working session, not the redirect itself.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "newperson@example.com"
    assert me.json()["data"]["role"] == "user"


def test_oauth_exchange_code_is_single_use(client, monkeypatch):
    response = _run_google_oauth_success(
        client, monkeypatch, email="onetime@example.com", provider_id="google-999"
    )
    code = _redirect_query(response)["code"][0]

    first = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert first.status_code == 200

    second = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert second.status_code == 400
    assert second.json()["success"] is False


def test_oauth_exchange_rejects_unknown_code(client):
    response = client.post("/api/auth/oauth/exchange", json={"code": "not-a-real-code-at-all"})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_oauth_exchange_rejects_expired_code(client, monkeypatch):
    response = _run_google_oauth_success(
        client, monkeypatch, email="expired@example.com", provider_id="google-expired"
    )
    code = _redirect_query(response)["code"][0]

    import app.services.oauth_service as oauth_service

    monkeypatch.setattr(oauth_service, "LOGIN_CODE_TTL_SECONDS", -1)
    # Re-issuing with a negative TTL doesn't retroactively expire the code
    # already minted above, so instead travel the existing row's clock back.
    from datetime import datetime, timedelta, timezone

    from app.database.database import SessionLocal
    from app.models.oauth_login_code import OAuthLoginCode

    db = SessionLocal()
    try:
        row = db.query(OAuthLoginCode).first()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    exchange = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert exchange.status_code == 400


def test_unauthenticated_request_cannot_reach_protected_endpoint(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_google_callback_links_to_existing_verified_email_and_can_authenticate(client, monkeypatch):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "supersecret1"},
    )

    response = _run_google_oauth_success(
        client, monkeypatch, email="jane@example.com", provider_id="google-456", email_verified=True
    )
    code = _redirect_query(response)["code"][0]

    exchange = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert exchange.status_code == 200
    token = exchange.json()["data"]["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "jane@example.com"

    # Still exactly one account for that email/password login keeps working.
    password_login = client.post(
        "/api/auth/login", json={"email": "jane@example.com", "password": "supersecret1"}
    )
    assert password_login.status_code == 200


def test_google_callback_does_not_auto_link_unverified_email(client, monkeypatch):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "supersecret1"},
    )

    response = _run_google_oauth_success(
        client, monkeypatch, email="jane@example.com", provider_id="google-789", email_verified=False
    )
    assert response.status_code == 302
    assert "oauth_error" in _redirect_query(response)


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
    code = _redirect_query(response)["code"][0]

    exchange = client.post("/api/auth/oauth/exchange", json={"code": code})
    assert exchange.status_code == 200
    token = exchange.json()["data"]["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "private@example.com"
