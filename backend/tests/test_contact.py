from models import Lead


def test_valid_contact_is_normalized_stored_and_notified(app, client, valid_contact, monkeypatch):
    sent = []
    monkeypatch.setattr("api.public.send_lead_notification", lambda lead: sent.append(lead.id))
    response = client.post("/api/contact", json=valid_contact, headers={"Idempotency-Key": "request-one"})
    assert response.status_code == 201
    with app.app_context():
        lead = Lead.query.one()
        assert lead.email == "ama@example.com"
        assert lead.status == "new"
    assert sent == [1]


def test_contact_validation_failure_does_not_store(app, client, valid_contact, monkeypatch):
    valid_contact["message"] = "Too short"
    monkeypatch.setattr("api.public.send_lead_notification", lambda lead: None)
    response = client.post("/api/contact", json=valid_contact)
    assert response.status_code == 422
    assert "message" in response.get_json()["error"]["fields"]
    with app.app_context():
        assert Lead.query.count() == 0


def test_duplicate_idempotency_key_does_not_duplicate_lead(app, client, valid_contact, monkeypatch):
    monkeypatch.setattr("api.public.send_lead_notification", lambda lead: None)
    headers = {"Idempotency-Key": "same-request"}
    assert client.post("/api/contact", json=valid_contact, headers=headers).status_code == 201
    assert client.post("/api/contact", json=valid_contact, headers=headers).status_code == 200
    with app.app_context():
        assert Lead.query.count() == 1


def test_email_failure_keeps_stored_lead(app, client, valid_contact, monkeypatch):
    from services.email import EmailDeliveryError
    monkeypatch.setattr("api.public.send_lead_notification", lambda lead: (_ for _ in ()).throw(EmailDeliveryError()))
    response = client.post("/api/contact", json=valid_contact)
    assert response.status_code == 202
    assert response.get_json()["data"]["notification_delayed"] is True
    with app.app_context():
        assert Lead.query.count() == 1


def test_contact_rate_limit(client, valid_contact, monkeypatch):
    monkeypatch.setattr("api.public.send_lead_notification", lambda lead: None)
    statuses = [client.post("/api/contact", json=valid_contact, headers={"Idempotency-Key": f"rate-{index}"}).status_code for index in range(6)]
    assert statuses[-1] == 429

