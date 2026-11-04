EXP_PAYLOAD = {
    "title": "Full Stack Web Development Intern",
    "organization": "Zeravia",
    "experience_type": "Internship",
    "start_date": "2026-08-05",
    "end_date": None,
    "is_current": True,
    "description": "Building modern web applications.",
    "link_url": "https://www.linkedin.com/company/mood-indigo/",
    "display_order": 1,
}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create(client, token, **overrides):
    res = client.post("/api/experiences", json={**EXP_PAYLOAD, **overrides}, headers=auth(token))
    assert res.status_code == 201, res.text
    return res.json()["data"]


def test_public_list_is_empty_on_fresh_database(client):
    response = client.get("/api/experiences")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_write_endpoints_require_admin(client):
    assert client.post("/api/experiences", json=EXP_PAYLOAD).status_code == 401
    assert client.put("/api/experiences/1", json={"title": "x"}).status_code == 401
    assert client.delete("/api/experiences/1").status_code == 401


def test_list_is_ordered_by_display_order(client, admin_token):
    create(client, admin_token, title="Third", display_order=2)
    create(client, admin_token, title="First", display_order=0)
    create(client, admin_token, title="Second", display_order=1)

    items = client.get("/api/experiences").json()["data"]
    assert [item["title"] for item in items] == ["First", "Second", "Third"]


def test_create_returns_all_fields_and_null_optionals(client, admin_token):
    item = create(client, admin_token, end_date=None, link_url=None, is_current=False)
    assert item["start_date"] == "2026-08-05"
    assert item["end_date"] is None
    assert item["link_url"] is None
    assert item["is_current"] is False
    assert item["display_order"] == 1
    assert item["created_at"] and item["updated_at"]


def test_get_single_and_not_found(client, admin_token):
    item = create(client, admin_token)
    assert client.get(f"/api/experiences/{item['id']}").json()["data"]["title"] == item["title"]
    assert client.get("/api/experiences/9999").status_code == 404


def test_partial_update_keeps_other_fields(client, admin_token):
    item = create(client, admin_token)
    res = client.put(
        f"/api/experiences/{item['id']}", json={"is_current": False}, headers=auth(admin_token)
    )
    assert res.status_code == 200
    updated = res.json()["data"]
    assert updated["is_current"] is False
    assert updated["organization"] == "Zeravia"
    assert updated["start_date"] == "2026-08-05"
    assert updated["link_url"] == EXP_PAYLOAD["link_url"]


def test_update_can_clear_nullable_fields(client, admin_token):
    item = create(client, admin_token)
    res = client.put(
        f"/api/experiences/{item['id']}",
        json={"start_date": None, "link_url": None},
        headers=auth(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["data"]["start_date"] is None
    assert res.json()["data"]["link_url"] is None


def test_update_rejects_null_required_field(client, admin_token):
    item = create(client, admin_token)
    res = client.put(
        f"/api/experiences/{item['id']}", json={"title": None}, headers=auth(admin_token)
    )
    assert res.status_code == 422
    assert res.json()["message"] == "title cannot be empty"


def test_delete_removes_item(client, admin_token):
    item = create(client, admin_token)
    assert client.delete(f"/api/experiences/{item['id']}", headers=auth(admin_token)).status_code == 200
    assert client.get(f"/api/experiences/{item['id']}").status_code == 404


def test_rejects_unsafe_link_url(client, admin_token):
    res = client.post(
        "/api/experiences",
        json={**EXP_PAYLOAD, "link_url": "javascript:alert(1)"},
        headers=auth(admin_token),
    )
    assert res.status_code == 422
