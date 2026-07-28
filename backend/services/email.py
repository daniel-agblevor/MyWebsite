import html
import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def send_lead_notification(lead):
    api_key = current_app.config["RESEND_API_KEY"]
    if not api_key:
        raise EmailDeliveryError("Email provider is not configured")
    safe = {name: html.escape(str(getattr(lead, name) or "")) for name in ("name", "email", "phone", "service_interest", "message")}
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": current_app.config["RESEND_FROM_EMAIL"],
            "to": [current_app.config["CONTACT_NOTIFICATION_TO"]],
            "subject": f"New website inquiry: {safe['service_interest']}",
            "html": (
                f"<h2>New website inquiry</h2><p><strong>Name:</strong> {safe['name']}</p>"
                f"<p><strong>Email:</strong> {safe['email']}</p><p><strong>Phone:</strong> {safe['phone']}</p>"
                f"<p><strong>Service:</strong> {safe['service_interest']}</p><p><strong>Message:</strong><br>{safe['message']}</p>"
            ),
        },
        timeout=10,
    )
    if response.status_code not in {200, 201, 202}:
        logger.warning("Lead notification delivery failed with provider status %s", response.status_code)
        raise EmailDeliveryError("Provider rejected the notification")
    return response.json()

