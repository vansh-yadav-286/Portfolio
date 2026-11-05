PROJECT_PAYLOAD = {
    "title": "Test Project",
    "description": "A project used for testing.",
    "technologies": "Python,FastAPI",
    "category": "Backend",
    "featured": True,
}


def test_public_can_list_projects(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == []


def test_create_project_requires_admin(client):
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 401


def test_create_project_requires_csrf_header(client, admin_csrf):
    # admin_csrf logs `client` in but this request deliberately omits the header.
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 403


def test_non_admin_cannot_create_project(client, user_csrf):
    response = client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers={"X-CSRF-Token": user_csrf}
    )
    assert response.status_code == 403


def test_admin_can_create_list_update_delete_project(client, admin_csrf):
    headers = {"X-CSRF-Token": admin_csrf}

    create_res = client.post("/api/projects", json=PROJECT_PAYLOAD, headers=headers)
    assert create_res.status_code == 201
    project_id = create_res.json()["data"]["id"]

    list_res = client.get("/api/projects")
    assert len(list_res.json()["data"]) == 1

    get_res = client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["title"] == "Test Project"

    update_res = client.put(
        f"/api/projects/{project_id}", json={"title": "Updated Title"}, headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["title"] == "Updated Title"

    delete_res = client.delete(f"/api/projects/{project_id}", headers=headers)
    assert delete_res.status_code == 200

    missing_res = client.get(f"/api/projects/{project_id}")
    assert missing_res.status_code == 404


def test_get_nonexistent_project_returns_404(client):
    response = client.get("/api/projects/999")
    assert response.status_code == 404


def test_create_project_validates_input(client, admin_csrf):
    response = client.post(
        "/api/projects", json={"title": ""}, headers={"X-CSRF-Token": admin_csrf}
    )
    assert response.status_code == 422
