from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.audit_service import AuditService
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService


class CommunicationService:
    def __init__(
        self,
        repository,
        audit: AuditService,
        email_service: EmailService | None = None,
        whatsapp_service: WhatsAppService | None = None,
    ):
        self.repository = repository
        self.audit = audit
        self.email_service = email_service or EmailService()
        self.whatsapp_service = whatsapp_service or WhatsAppService()

    def send(self, user: dict, payload: dict[str, Any], channels: list[str]) -> list[dict]:
        logs = []
        for channel in channels:
            connector = self.repository.get_connector(channel, user.get("id"))
            if channel == "email":
                result = self.email_service.send(payload, connector)
            elif channel == "whatsapp":
                result = self.whatsapp_service.send(payload, connector)
            else:
                continue
            log = self.repository.add_communication_log({
                "channel": channel,
                "recipient_name": payload.get("recipient_name", ""),
                "recipient_email": payload.get("recipient_email", ""),
                "recipient_phone": payload.get("recipient_phone", ""),
                "subject": payload.get("subject", ""),
                "message_body": payload.get("message_body", ""),
                "status": result["status"],
                "provider": result["provider"],
                "related_module": payload.get("related_module", "general"),
                "related_record_id": payload.get("related_record_id", ""),
                "sent_by_user_id": user.get("id"),
                "sent_by_name": user.get("name", ""),
                "sent_by_email": user.get("email", ""),
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "error_message": result.get("error_message", ""),
                "metadata": {
                    **(result.get("metadata") or {}),
                    "attachments": payload.get("attachments", []),
                },
            })
            self.audit.record(
                f"communication.{channel}.{result['status']}",
                result["status"],
                actor=user.get("email", ""),
                details={
                    "communication_log_id": log["id"],
                    "related_module": payload.get("related_module", "general"),
                    "related_record_id": payload.get("related_record_id", ""),
                    "recipient_email": payload.get("recipient_email", ""),
                    "recipient_phone": payload.get("recipient_phone", ""),
                    "provider": result["provider"],
                    "actor_user_id": user.get("id"),
                    "actor_role": user.get("role"),
                },
            )
            logs.append(log)
        return logs
