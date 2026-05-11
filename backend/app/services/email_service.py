from __future__ import annotations

import json
import smtplib
import urllib.request
from email.message import EmailMessage
from typing import Any

from app.core.config import settings


class EmailService:
    def provider_from_connector(self, connector: dict | None = None) -> str:
        configured = str((connector or {}).get("provider") or settings.email_provider or "mock").strip()
        if configured.lower() in {"smtp", "sendgrid", "mock email"}:
            return configured
        return "Mock Email" if configured.lower() == "mock" else configured

    def is_configured(self, provider: str) -> bool:
        normalized = provider.strip().lower()
        if normalized == "smtp":
            return bool(settings.smtp_host and settings.email_from_address)
        if normalized == "sendgrid":
            return bool(settings.sendgrid_api_key and settings.email_from_address)
        return False

    def send(self, payload: dict[str, Any], connector: dict | None = None) -> dict:
        provider = self.provider_from_connector(connector)
        if not self.is_configured(provider):
            return {
                "channel": "email",
                "provider": provider or "Mock Email",
                "status": "mock_sent",
                "error_message": "",
                "metadata": {"mode": "mock", "reason": "Email credentials are not configured"},
            }
        if provider.strip().lower() == "smtp":
            return self._send_smtp(payload, provider)
        if provider.strip().lower() == "sendgrid":
            return self._send_sendgrid(payload, provider)
        return {
            "channel": "email",
            "provider": "Mock Email",
            "status": "mock_sent",
            "error_message": "",
            "metadata": {"mode": "mock"},
        }

    def _send_smtp(self, payload: dict[str, Any], provider: str) -> dict:
        try:
            message = EmailMessage()
            message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
            message["To"] = payload.get("recipient_email", "")
            message["Subject"] = payload.get("subject") or "Agent Concierge message"
            message.set_content(payload.get("message_body", ""))
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return {"channel": "email", "provider": provider, "status": "sent", "error_message": "", "metadata": {"mode": "smtp"}}
        except Exception as exc:
            return {"channel": "email", "provider": provider, "status": "failed", "error_message": str(exc), "metadata": {"mode": "smtp"}}

    def _send_sendgrid(self, payload: dict[str, Any], provider: str) -> dict:
        try:
            body = {
                "personalizations": [{"to": [{"email": payload.get("recipient_email", "")}]}],
                "from": {"email": settings.email_from_address, "name": settings.email_from_name},
                "subject": payload.get("subject") or "Agent Concierge message",
                "content": [{"type": "text/plain", "value": payload.get("message_body", "")}],
            }
            request = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                status = "sent" if 200 <= int(response.status) < 300 else "failed"
            return {"channel": "email", "provider": provider, "status": status, "error_message": "", "metadata": {"mode": "sendgrid"}}
        except Exception as exc:
            return {"channel": "email", "provider": provider, "status": "failed", "error_message": str(exc), "metadata": {"mode": "sendgrid"}}
