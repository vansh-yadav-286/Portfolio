def test_me_requires_session(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_admin_for_admin_email(client, admin_csrf):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "admin@example.com"
    assert data["role"] == "admin"
    assert data["csrf_token"] == admin_csrf


def test_me_returns_user_for_non_admin_email(client, user_csrf):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "visitor@example.com"
    assert data["role"] == "user"


def test_logout_requires_csrf_header(client, admin_csrf):
    response = client.post("/api/auth/logout")
    assert response.status_code == 403


def test_logout_clears_session(client, admin_csrf):
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    assert response.status_code == 200
    assert response.json()["success"] is True
    # The server's Set-Cookie must actively expire the cookie (not just omit
    # it) - this is what makes a real browser drop it. httpx's TestClient
    # cookie jar doesn't apply Max-Age=0 itself, so that part isn't checked
    # through a follow-up request here.
    set_cookie = response.headers.get("set-cookie", "")
    assert "session=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_tampered_session_cookie_is_rejected(client):
    client.cookies.set("session", "not-a-real-token")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
