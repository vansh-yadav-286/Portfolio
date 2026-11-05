CONTACT_PAYLOAD = {
    "name": "Visitor",
    "email": "visitor@example.com",
    "subject": "Hello",
    "message": "This is a test message.",
}


def _configure_smtp(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "contact_email_to", "owner@example.com")
    monkeypatch.setattr(settings, "contact_email_from", "noreply@example.com")


def test_contact_is_not_sent_when_smtp_unconfigured(client):
    # No database means a submission with no SMTP configured has nowhere to
    # go at all - this must fail loudly (503), never silently succeed.
    response = client.post("/api/contact", json=CONTACT_PAYLOAD)
    assert response.status_code == 503


def test_public_can_submit_contact_message(client, monkeypatch):
    _configure_smtp(monkeypatch)
    sent = {}

    def fake_send(name, email, subject, message):
        sent.update(name=name, email=email, subject=subject, message=message)

    monkeypatch.setattr("app.services.contact_service.send_contact_email", fake_send)

    response = client.post("/api/contact", json=CONTACT_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert sent == CONTACT_PAYLOAD


def test_contact_requires_valid_email(client, monkeypatch):
    _configure_smtp(monkeypatch)
    payload = {**CONTACT_PAYLOAD, "email": "not-an-email"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_failure_returns_502_not_a_stack_trace(client, monkeypatch):
    _configure_smtp(monkeypatch)

    def fake_send(*args):
        from app.services.email_service import EmailSendError

        raise EmailSendError("Could not send your message right now. Please try again later.")

    monkeypatch.setattr("app.services.contact_service.send_contact_email", fake_send)

    response = client.post("/api/contact", json=CONTACT_PAYLOAD)
    assert response.status_code == 502
    assert response.json()["success"] is False


def test_there_is_no_admin_inbox_for_messages(client, admin_csrf):
    # Nothing is stored, so there is nothing to list/moderate - only POST
    # /api/contact exists now. GET on that same path is 405 Method Not
    # Allowed; the by-id routes don't exist at all, so those are 404.
    assert client.get("/api/contact").status_code == 405
    assert client.patch("/api/contact/1", json={"status": "read"}).status_code == 404
    assert client.delete("/api/contact/1").status_code == 404
