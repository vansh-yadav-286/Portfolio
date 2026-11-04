HACK_PAYLOAD = {
    "title": "ET AI Hackathon",
    "type": "hackathon",
    "description": "AI hackathon, 2026.",
    "icon": "bolt",
    "certificate_url": "Workshop & Hackathon/ET-AI_Hackathon_2026_Certificate_Vansh_Yadav.pdf",
}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create(client, token, **overrides):
    res = client.post("/api/hackathons", json={**HACK_PAYLOAD, **overrides}, headers=auth(token))
    assert res.status_code == 201, res.text
    return res.json()["data"]


def test_public_list_is_empty_on_fresh_database(client):
    response = client.get("/api/hackathons")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_manage_endpoints_require_admin(client):
    assert client.get("/api/hackathons/manage").status_code == 401
    assert client.post("/api/hackathons", json=HACK_PAYLOAD).status_code == 401
    assert client.put("/api/hackathons/1", json={"title": "x"}).status_code == 401
    assert client.delete("/api/hackathons/1").status_code == 401


def test_public_list_hides_invisible_and_orders_by_display_order(client, admin_token):
    create(client, admin_token, title="Third", display_order=2)
    create(client, admin_token, title="Hidden", display_order=1, is_visible=False)
    create(client, admin_token, title="First", display_order=0)

    public = client.get("/api/hackathons").json()["data"]
    assert [item["title"] for item in public] == ["First", "Third"]

    manage = client.get("/api/hackathons/manage", headers=auth(admin_token)).json()["data"]
    assert [item["title"] for item in manage] == ["First", "Hidden", "Third"]


def test_edit_visibility_and_display_order(client, admin_token):
    item = create(client, admin_token, title="Workshop A", display_order=0)

    res = client.put(f"/api/hackathons/{item['id']}", json={"is_visible": False, "display_order": 5}, headers=auth(admin_token))
    assert res.status_code == 200
    assert res.json()["data"]["is_visible"] is False
    assert res.json()["data"]["display_order"] == 5
    assert client.get("/api/hackathons").json()["data"] == []


def test_subitems_round_trip(client, admin_token):
    subitems = [{"title": "Blue Dart", "certificate_url": "Workshop & Hackathon/a.pdf"}]
    item = create(client, admin_token, type="workshop", subitems=subitems)
    assert item["subitems"] == subitems

    public = client.get("/api/hackathons").json()["data"]
    assert public[0]["subitems"] == subitems


def test_delete_removes_item(client, admin_token):
    item = create(client, admin_token)
    assert client.delete(f"/api/hackathons/{item['id']}", headers=auth(admin_token)).status_code == 200
    assert client.get(f"/api/hackathons/manage", headers=auth(admin_token)).json()["data"] == []
    assert client.delete(f"/api/hackathons/{item['id']}", headers=auth(admin_token)).status_code == 404


def test_validation_rejects_bad_input(client, admin_token):
    headers = auth(admin_token)
    assert client.post("/api/hackathons", json={**HACK_PAYLOAD, "type": "meetup"}, headers=headers).status_code == 422
    assert client.post("/api/hackathons", json={**HACK_PAYLOAD, "icon": "skull"}, headers=headers).status_code == 422
    assert client.post("/api/hackathons", json={**HACK_PAYLOAD, "event_url": "javascript:alert(1)"}, headers=headers).status_code == 422
    assert client.post("/api/hackathons", json={**HACK_PAYLOAD, "title": ""}, headers=headers).status_code == 422

    item = create(client, admin_token)
    assert client.put(f"/api/hackathons/{item['id']}", json={"title": None}, headers=headers).status_code == 422
    assert client.put(f"/api/hackathons/{item['id']}", json={"is_visible": None}, headers=headers).status_code == 422


def test_update_missing_item_returns_404(client, admin_token):
    res = client.put("/api/hackathons/999", json={"title": "x"}, headers=auth(admin_token))
    assert res.status_code == 404
