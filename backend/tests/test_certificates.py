CERT_PAYLOAD = {
    "title": "Azure Fundamentals",
    "issuer": "Microsoft",
    "credential_id": "AZ-900-123",
}


def test_public_can_list_certificates(client):
    response = client.get("/api/certificates")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_create_certificate_requires_admin(client):
    response = client.post("/api/certificates", json=CERT_PAYLOAD)
    assert response.status_code == 401


def test_admin_can_manage_certificate_lifecycle(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_res = client.post("/api/certificates", json=CERT_PAYLOAD, headers=headers)
    assert create_res.status_code == 201
    cert_id = create_res.json()["data"]["id"]

    update_res = client.put(
        f"/api/certificates/{cert_id}", json={"issuer": "Microsoft Learn"}, headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["issuer"] == "Microsoft Learn"

    delete_res = client.delete(f"/api/certificates/{cert_id}", headers=headers)
    assert delete_res.status_code == 200

    missing_res = client.get(f"/api/certificates/{cert_id}")
    assert missing_res.status_code == 404
