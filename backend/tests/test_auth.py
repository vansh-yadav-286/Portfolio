def test_register_new_user(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "jane@example.com"
    assert body["data"]["role"] == "user"


def test_register_duplicate_email_rejected(client):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "supersecret1"},
    )
    response = client.post(
        "/api/auth/register",
        json={"name": "Jane Two", "email": "jane@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 409
    assert response.json()["success"] is False


def test_admin_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-test-password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


def test_login_invalid_password(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, admin_token):
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "admin@example.com"
    assert response.json()["data"]["role"] == "admin"


def test_logout(client, admin_token):
    response = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
