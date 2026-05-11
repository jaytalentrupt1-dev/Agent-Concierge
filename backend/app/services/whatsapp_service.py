from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import settings


class WhatsAppService:
    def provider_from_connector(self, connector: dict | None = None) -> str:
        configured = str((connector or {}).get("provider") or settings.whatsapp_provider or "mock").strip()
        if configured.lower() == "mock":
            return "Mock WhatsApp"
        return configured or "Mock WhatsApp"

    def is_configured(self, provider: str) -> bool:
        normalized = provider.strip().lower()
        if normalized == "twilio whatsapp":
            return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from)
        if normalized == "whatsapp cloud api":
            return bool(settings.whatsapp_cloud_access_token and settings.whatsapp_phone_number_id)
        return False

    def send(self, payload: dict[str, Any], connector: dict | None = None) -> dict:
        provider = self.provider_from_connector(connector)
        if not self.is_configured(provider):
            return {
                "channel": "whatsapp",
                "provider": provider or "Mock WhatsApp",
                "status": "mock_sent",
                "error_message": "",
                "metadata": {"mode": "mock", "reason": "WhatsApp credentials are not configured"},
            }
        if provider.strip().lower() == "twilio whatsapp":
            return self._send_twilio(payload, provider)
        if provider.strip().lower() == "whatsapp cloud api":
            return self._send_cloud_api(payload, provider)
        return {"channel": "whatsapp", "provider": "Mock WhatsApp", "status": "mock_sent", "error_message": "", "metadata": {"mode": "mock"}}

    def _send_twilio(self, payload: dict[str, Any], provider: str) -> dict:
        try:
            account_sid = settings.twilio_account_sid
            token = settings.twilio_auth_token
            data = urllib.parse.urlencode({
                "From": settings.twilio_whatsapp_from,
                "To": f"whatsapp:{payload.get('recipient_phone', '')}",
                "Body": payload.get("message_body", ""),
            }).encode("utf-8")
            request = urllib.request.Request(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                data=data,
                method="POST",
            )
            auth = base64.b64encode(f"{account_sid}:{token}".encode("utf-8")).decode("ascii")
            request.add_header("Authorization", f"Basic {auth}")
            with urllib.request.urlopen(request, timeout=10) as response:
                status = "sent" if 200 <= int(response.status) < 300 else "failed"
            return {"channel": "whatsapp", "provider": provider, "status": status, "error_message": "", "metadata": {"mode": "twilio"}}
        except Exception as exc:
            return {"channel": "whatsapp", "provider": provider, "status": "failed", "error_message": str(exc), "metadata": {"mode": "twilio"}}

    def _send_cloud_api(self, payload: dict[str, Any], provider: str) -> dict:
        try:
            body = {
                "messaging_product": "whatsapp",
                "to": payload.get("recipient_phone", ""),
                "type": "text",
                "text": {"body": payload.get("message_body", "")},
            }
            request = urllib.request.Request(
                f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.whatsapp_cloud_access_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                status = "sent" if 200 <= int(response.status) < 300 else "failed"
            return {"channel": "whatsapp", "provider": provider, "status": status, "error_message": "", "metadata": {"mode": "whatsapp_cloud_api"}}
        except Exception as exc:
            return {"channel": "whatsapp", "provider": provider, "status": "failed", "error_message": str(exc), "metadata": {"mode": "whatsapp_cloud_api"}}
