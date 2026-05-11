from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROLES = {"admin", "it_manager", "finance_manager", "employee"}

TASK_TYPES = {
    "meeting_management",
    "vendor_management",
    "expense_management",
    "travel_management",
    "inventory_management",
    "it_request",
    "document_management",
    "report_generation",
    "floor_activity_management",
}

ROLE_LABELS = {
    "admin": "Admin",
    "finance_manager": "Finance Manager",
    "it_manager": "IT Manager",
    "employee": "Employee",
}


@dataclass(frozen=True)
class ApprovalRoute:
    task_type: str
    priority: str
    risk_level: str
    status: str
    requester_user_id: int | None
    assigned_role: str
    required_approval_roles: list[str]
    approval_required: bool
    approval_reason: str
    approval_type: str | None = None

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "status": self.status,
            "requester_user_id": self.requester_user_id,
            "assigned_role": self.assigned_role,
            "required_approval_roles": self.required_approval_roles,
            "approval_required": self.approval_required,
            "approval_reason": self.approval_reason,
            "approval_type": self.approval_type,
            "required_role_label": required_role_label(self.required_approval_roles),
        }


def required_role_label(roles: list[str]) -> str:
    if not roles:
        return "No approval required"
    labels = [ROLE_LABELS.get(role, role.title()) for role in roles]
    return f"Requires {'/'.join(labels)} approval"


class ApprovalRulesService:
    """Central approval and routing rules for mocked admin requests."""

    APPROVAL_RULES = {
        "expense_approval": {
            "task_type": "expense_management",
            "assigned_role": "finance_manager",
            "required_roles": ["finance_manager", "admin"],
            "reason": "Expense approvals require Finance Manager/Admin approval before posting.",
            "risk_level": "high",
            "priority": "high",
        },
        "payment": {
            "task_type": "expense_management",
            "assigned_role": "finance_manager",
            "required_roles": ["finance_manager", "admin"],
            "reason": "Payments require Finance Manager/Admin approval before execution.",
            "risk_level": "high",
            "priority": "high",
        },
        "invoice_mismatch": {
            "task_type": "expense_management",
            "assigned_role": "finance_manager",
            "required_roles": ["finance_manager", "admin"],
            "reason": "Invoice mismatches require Finance Manager/Admin approval before resolution.",
            "risk_level": "high",
            "priority": "high",
        },
        "reimbursement": {
            "task_type": "expense_management",
            "assigned_role": "finance_manager",
            "required_roles": ["finance_manager", "admin"],
            "reason": "Reimbursements require Finance Manager/Admin approval before posting.",
            "risk_level": "high",
            "priority": "high",
        },
        "external_vendor_email": {
            "task_type": "vendor_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "External vendor communication requires Admin approval before send.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "vendor_followup": {
            "task_type": "vendor_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Vendor follow-up emails require Admin approval before send.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "meeting_approval": {
            "task_type": "meeting_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Meeting-related approvals require Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "vendor_contract_renewal": {
            "task_type": "vendor_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Vendor contract renewals require Admin approval before commitment.",
            "risk_level": "high",
            "priority": "high",
        },
        "vendor_contract_change": {
            "task_type": "vendor_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Vendor contract changes require Admin approval before commitment.",
            "risk_level": "high",
            "priority": "high",
        },
        "contract_change": {
            "task_type": "vendor_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Contract changes require Admin approval before commitment.",
            "risk_level": "high",
            "priority": "high",
        },
        "travel_booking": {
            "task_type": "travel_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Travel bookings require Admin approval before confirmation.",
            "risk_level": "high",
            "priority": "high",
        },
        "inventory_reorder": {
            "task_type": "inventory_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Inventory reorders require Admin approval before purchase.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "it_equipment_reorder": {
            "task_type": "inventory_management",
            "assigned_role": "it_manager",
            "required_roles": ["it_manager", "admin"],
            "reason": "IT equipment inventory reorders require IT Manager/Admin approval before purchase.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "password_request": {
            "task_type": "it_request",
            "assigned_role": "it_manager",
            "required_roles": ["it_manager", "admin"],
            "reason": "Password workflow requests require IT Manager/Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "account_access": {
            "task_type": "it_request",
            "assigned_role": "it_manager",
            "required_roles": ["it_manager", "admin"],
            "reason": "Account access requests require IT Manager/Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "device_request": {
            "task_type": "it_request",
            "assigned_role": "it_manager",
            "required_roles": ["it_manager", "admin"],
            "reason": "Device requests require IT Manager/Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "it_support": {
            "task_type": "it_request",
            "assigned_role": "it_manager",
            "required_roles": ["it_manager", "admin"],
            "reason": "IT support actions require IT Manager/Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "floor_activity": {
            "task_type": "floor_activity_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Floor activity approvals require Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "floor_activity_issue": {
            "task_type": "floor_activity_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Floor activity issues require Admin approval.",
            "risk_level": "medium",
            "priority": "normal",
        },
        "confidential_document_sharing": {
            "task_type": "document_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Confidential document sharing requires Admin approval.",
            "risk_level": "high",
            "priority": "high",
        },
        "file_deletion": {
            "task_type": "document_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "File deletion requires Admin approval and must never run automatically.",
            "risk_level": "critical",
            "priority": "critical",
        },
        "legal_compliance_decision": {
            "task_type": "document_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Legal or compliance decisions require Admin approval.",
            "risk_level": "critical",
            "priority": "critical",
        },
        "policy_exception": {
            "task_type": "document_management",
            "assigned_role": "admin",
            "required_roles": ["admin"],
            "reason": "Policy exceptions require Admin approval.",
            "risk_level": "critical",
            "priority": "critical",
        },
    }

    TASK_DEFAULTS = {
        "meeting_management": "admin",
        "vendor_management": "admin",
        "expense_management": "finance_manager",
        "travel_management": "admin",
        "inventory_management": "admin",
        "it_request": "it_manager",
        "document_management": "admin",
        "report_generation": "admin",
        "floor_activity_management": "admin",
    }

    ALIASES = {
        "vendor_follow_up": "vendor_followup",
        "vendor_followup_email": "vendor_followup",
        "external_vendor_email": "external_vendor_email",
    }

    IT_EQUIPMENT_TERMS = {
        "laptop",
        "monitor",
        "keyboard",
        "mouse",
        "device",
        "printer",
        "router",
        "server",
        "phone",
        "tablet",
        "badge scanner",
    }

    def route_request(
        self,
        *,
        message: str,
        requester_user_id: int | None,
        task_type: str | None = None,
        approval_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        metadata = metadata or {}
        detected_task_type = self._normalize_task_type(task_type) or self.classify_task_type(message)
        detected_approval_type = self._normalize_approval_type(
            approval_type or self.detect_approval_type(message, metadata)
        )
        route = self.apply_rule(
            task_type=detected_task_type,
            approval_type=detected_approval_type,
            requester_user_id=requester_user_id,
            message=message,
            metadata=metadata,
        )
        return route.to_dict()

    def apply_rule(
        self,
        *,
        task_type: str,
        approval_type: str | None,
        requester_user_id: int | None,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRoute:
        metadata = metadata or {}
        canonical_task_type = self._normalize_task_type(task_type) or "report_generation"
        canonical_approval_type = self._normalize_approval_type(approval_type)

        if canonical_approval_type == "inventory_reorder" and self._is_it_equipment(message, metadata):
            canonical_approval_type = "it_equipment_reorder"

        rule = self.APPROVAL_RULES.get(canonical_approval_type or "")
        if rule:
            return ApprovalRoute(
                task_type=rule["task_type"],
                priority=rule["priority"],
                risk_level=rule["risk_level"],
                status="pending_approval",
                requester_user_id=requester_user_id,
                assigned_role=rule["assigned_role"],
                required_approval_roles=list(rule["required_roles"]),
                approval_required=True,
                approval_reason=rule["reason"],
                approval_type=canonical_approval_type,
            )

        assigned_role = self.TASK_DEFAULTS.get(canonical_task_type, "admin")
        return ApprovalRoute(
            task_type=canonical_task_type,
            priority="normal",
            risk_level="low",
            status="routed",
            requester_user_id=requester_user_id,
            assigned_role=assigned_role,
            required_approval_roles=[],
            approval_required=False,
            approval_reason="",
            approval_type=None,
        )

    def approval_metadata(self, approval_type: str) -> dict:
        route = self.apply_rule(
            task_type="report_generation",
            approval_type=approval_type,
            requester_user_id=None,
        ).to_dict()
        if not route["approval_required"]:
            route.update(
                {
                    "assigned_role": "admin",
                    "required_approval_roles": ["admin"],
                    "required_role_label": required_role_label(["admin"]),
                    "approval_reason": "Unknown approval requests require Admin approval.",
                    "priority": "high",
                    "risk_level": "high",
                    "approval_required": True,
                }
            )
        return {
            "required_roles": route["required_approval_roles"],
            "required_role_label": route["required_role_label"],
            "approval_reason": route["approval_reason"],
            "assigned_role": route["assigned_role"],
            "task_type": route["task_type"],
            "priority": route["priority"],
            "risk_level": route["risk_level"],
            "approval_required": route["approval_required"],
        }

    def classify_task_type(self, message: str) -> str:
        text = message.lower()
        if any(term in text for term in ["password", "account access", "device", "it support", "laptop"]):
            return "it_request"
        if any(term in text for term in ["expense", "reimbursement", "payment", "invoice"]):
            return "expense_management"
        if any(term in text for term in ["travel", "flight", "hotel", "trip"]):
            return "travel_management"
        if any(term in text for term in ["inventory", "stock", "reorder", "supplies", "cartridge", "cartridges", "toner"]):
            return "inventory_management"
        if any(term in text for term in ["floor", "facility", "facilities", "workplace"]):
            return "floor_activity_management"
        if any(term in text for term in ["vendor", "supplier", "contract"]):
            return "vendor_management"
        if any(term in text for term in ["remind", "reminder", "notify", "calendar", "schedule"]):
            return "meeting_management"
        if any(term in text for term in ["confidential", "delete file", "remove file", "document", "file"]):
            return "document_management"
        if any(term in text for term in ["meeting", "calendar", "schedule"]):
            return "meeting_management"
        if any(term in text for term in ["report", "dashboard", "status"]):
            return "report_generation"
        return "report_generation"

    def detect_approval_type(self, message: str, metadata: dict[str, Any] | None = None) -> str | None:
        metadata = metadata or {}
        text = message.lower()
        if "file" in text and any(term in text for term in ["delete", "remove", "destroy"]):
            return "file_deletion"
        if any(term in text for term in ["legal", "compliance"]):
            return "legal_compliance_decision"
        if "policy exception" in text or "override policy" in text:
            return "policy_exception"
        if "confidential" in text or "restricted document" in text:
            return "confidential_document_sharing"
        if "vendor" in text and "contract" in text and any(term in text for term in ["renew", "renewal"]):
            return "vendor_contract_renewal"
        if "contract" in text and any(term in text for term in ["change", "amend", "amendment", "terminate"]):
            return "vendor_contract_change" if "vendor" in text else "contract_change"
        if "invoice" in text and any(term in text for term in ["mismatch", "discrepancy", "difference"]):
            return "invoice_mismatch"
        if any(term in text for term in ["payment", "pay invoice", "wire transfer", "release funds"]):
            return "payment"
        if any(term in text for term in ["expense approval", "approve expense", "expense report"]):
            return "expense_approval"
        if "reimbursement" in text:
            return "reimbursement"
        if "vendor" in text and any(term in text for term in ["follow-up", "follow up", "email", "send"]):
            return "vendor_followup"
        if any(term in text for term in ["travel booking", "book travel", "book flight", "book hotel", "reserve flight"]):
            return "travel_booking"
        if any(term in text for term in ["inventory reorder", "reorder", "low stock", "restock", "cartridge", "cartridges", "toner"]):
            return "inventory_reorder"
        if "password" in text:
            return "password_request"
        if "account" in text and any(term in text for term in ["access", "create", "disable", "enable"]):
            return "account_access"
        if "device" in text or self._is_it_equipment(message, metadata):
            return "device_request"
        if "it support" in text:
            return "it_support"
        if "floor" in text and any(term in text for term in ["issue", "approval", "incident"]):
            return "floor_activity_issue"
        return None

    def _normalize_task_type(self, task_type: str | None) -> str | None:
        if not task_type:
            return None
        normalized = task_type.strip().lower()
        return normalized if normalized in TASK_TYPES else None

    def _normalize_approval_type(self, approval_type: str | None) -> str | None:
        if not approval_type:
            return None
        normalized = approval_type.strip().lower()
        return self.ALIASES.get(normalized, normalized)

    def _is_it_equipment(self, message: str, metadata: dict[str, Any] | None = None) -> bool:
        metadata = metadata or {}
        text = " ".join([message, str(metadata.get("category", "")), str(metadata.get("item", ""))]).lower()
        if any(term in text for term in ["cartridge", "cartridges", "toner", "paper", "supplies"]):
            return False
        return any(term in text for term in self.IT_EQUIPMENT_TERMS)
