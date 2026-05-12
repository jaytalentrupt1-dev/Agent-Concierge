from __future__ import annotations

import json
import smtplib
import base64
import urllib.request
from email.message import EmailMessage
from typing import Any

from app.core.config import settings


class EmailService:
    def provider_from_connector(self, connector: dict | None = None) -> str:
        configured = str((connector or {}).get("provider") or settings.email_provider or "mock").strip()
        if configured.lower() in {"smtp", "sendgrid", "mock email", "gmail"}:
            return configured
        return "Mock Email" if configured.lower() == "mock" else configured

    def is_configured(self, provider: str) -> bool:
        normalized = provider.strip().lower()
        if normalized == "smtp":
            return bool(settings.smtp_host and settings.email_from_address)
        if normalized == "sendgrid":
            return bool(settings.sendgrid_api_key and settings.email_from_address)
        if normalized == "gmail":
            return True
        return False

    def send(self, payload: dict[str, Any], connector: dict | None = None) -> dict:
        provider = self.provider_from_connector(connector)
        if provider.strip().lower() == "gmail":
            return self._send_gmail(payload, provider, connector)
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

    def _send_gmail(self, payload: dict[str, Any], provider: str, connector: dict | None = None) -> dict:
        config = (connector or {}).get("config", {}) or {}
        access_token = str(config.get("access_token") or "")
        sender = str(config.get("connected_email") or settings.email_from_address or "").strip()
        if not access_token:
            return {
                "channel": "email",
                "provider": provider,
                "status": "failed",
                "error_message": "Please connect your email in Settings first.",
                "metadata": {"mode": "gmail"},
            }
        try:
            message = EmailMessage()
            message["From"] = sender or "me"
            message["To"] = payload.get("recipient_email", "")
            message["Subject"] = payload.get("subject") or "Agent Concierge message"
            message.set_content(payload.get("message_body", ""))
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
            request = urllib.request.Request(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                data=json.dumps({"raw": raw_message}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                status = "sent" if 200 <= int(response.status) < 300 else "failed"
            return {"channel": "email", "provider": provider, "status": status, "error_message": "", "metadata": {"mode": "gmail", "from": sender}}
        except Exception as exc:
            return {"channel": "email", "provider": provider, "status": "failed", "error_message": str(exc), "metadata": {"mode": "gmail", "from": sender}}
