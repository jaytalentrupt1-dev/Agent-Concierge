from __future__ import annotations

from app.repositories.admin_repository import utc_now
from app.services.approval_rules import ApprovalRulesService
from app.services.audit_service import AuditService
from app.services.auth_service import can_approve


class ApprovalService:
    def __init__(
        self,
        repository,
        audit: AuditService,
        rules: ApprovalRulesService | None = None,
    ):
        self.repository = repository
        self.audit = audit
        self.rules = rules or ApprovalRulesService()

    def queue_external_email(
        self,
        *,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        body: str,
        related_meeting_id: int | None,
        requester_user_id: int | None = None,
    ) -> dict:
        route = self.rules.apply_rule(
            task_type="vendor_management",
            approval_type="external_vendor_email",
            requester_user_id=requester_user_id,
        ).to_dict()
        reason = route["approval_reason"]
        approval = self.repository.add_approval(
            {
                "approval_type": "external_vendor_email",
                "status": "pending",
                "risk_reason": reason,
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "original_body": body,
                "related_meeting_id": related_meeting_id,
            }
        )
        self.audit.record(
            "approval.queued",
            "pending",
            approval_required=True,
            approval_reason=reason,
            details={
                "approval_id": approval["id"],
                "approval_type": "external_vendor_email",
                "recipient_email": recipient_email,
                "assigned_role": route["assigned_role"],
                "required_approval_roles": route["required_approval_roles"],
            },
        )
        return approval

    def decide(
        self,
        approval_id: int,
        *,
        action: str,
        subject: str | None = None,
        body: str | None = None,
        reason: str | None = None,
        actor_user: dict | None = None,
    ) -> dict:
        approval = self.repository.get_approval(approval_id)
        if not approval:
            raise ValueError("Approval not found")
        if approval["status"] != "pending":
            raise ValueError("Only pending approvals can be edited, sent, or cancelled")
        if actor_user is not None and not can_approve(actor_user, approval):
            raise PermissionError(approval["required_role_label"])

        actor = actor_user["email"] if actor_user else "human_reviewer"
        actor_details = (
            {
                "actor_user_id": actor_user["id"],
                "actor_role": actor_user["role"],
                "actor_name": actor_user["name"],
            }
            if actor_user
            else {}
        )

        if action == "edit":
            updated = self.repository.update_approval(
                approval_id,
                subject=subject if subject is not None else approval["subject"],
                body=body if body is not None else approval["body"],
            )
            self.audit.record(
                "approval.edited",
                "pending",
                actor=actor,
                approval_required=True,
                approval_reason=updated["risk_reason"],
                details={"approval_id": approval_id, **actor_details},
            )
            return updated

        if action == "approve_send":
            updated = self.repository.update_approval(
                approval_id,
                subject=subject if subject is not None else approval["subject"],
                body=body if body is not None else approval["body"],
                status="sent",
                sent_at=utc_now(),
            )
            self.audit.record(
                "external_email.sent"
                if updated["approval_type"] == "external_vendor_email"
                else "approval.approved",
                "sent",
                actor=actor,
                approval_required=False,
                details={
                    "approval_id": approval_id,
                    "recipient_email": updated["recipient_email"],
                    "human_approved": True,
                    **actor_details,
                },
            )
            return updated

        if action == "cancel":
            updated = self.repository.update_approval(
                approval_id,
                status="cancelled",
                cancelled_reason=reason or "Cancelled by human reviewer.",
            )
            self.audit.record(
                "approval.cancelled",
                "cancelled",
                actor=actor,
                approval_required=True,
                approval_reason=updated["risk_reason"],
                details={
                    "approval_id": approval_id,
                    "reason": updated["cancelled_reason"],
                    **actor_details,
                },
            )
            return updated

        raise ValueError("Unsupported approval action")
