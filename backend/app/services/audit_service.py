from __future__ import annotations

from app.repositories.admin_repository import AdminRepository


class AuditService:
    def __init__(self, repository: AdminRepository):
        self.repository = repository

    def record(
        self,
        action: str,
        status: str,
        *,
        actor: str = "ai_admin_agent",
        approval_required: bool = False,
        approval_reason: str | None = None,
        details: dict | None = None,
    ) -> dict:
        return self.repository.add_audit_log(
            action=action,
            actor=actor,
            status=status,
            approval_required=approval_required,
            approval_reason=approval_reason,
            details=details or {},
        )
