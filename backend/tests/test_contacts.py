CONTACT_PAYLOAD = {
    "name": "Visitor",
    "email": "visitor@example.com",
    "subject": "Hello",
    "message": "This is a test message.",
}


def test_public_can_submit_contact_message(client):
    response = client.post("/api/contact", json=CONTACT_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "unread"


def test_contact_requires_valid_email(client):
    payload = {**CONTACT_PAYLOAD, "email": "not-an-email"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_listing_contact_messages_requires_admin(client):
    response = client.get("/api/contact")
    assert response.status_code == 401


def test_admin_can_list_and_moderate_messages(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/api/contact", json=CONTACT_PAYLOAD)

    list_res = client.get("/api/contact", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1
    message_id = list_res.json()["data"][0]["id"]

    patch_res = client.patch(
        f"/api/contact/{message_id}", json={"status": "read"}, headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "read"

    delete_res = client.delete(f"/api/contact/{message_id}", headers=headers)
    assert delete_res.status_code == 200
