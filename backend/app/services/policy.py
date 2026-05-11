from __future__ import annotations

APPROVAL_REASONS = {
    "external_vendor_email": "External vendor communication must be reviewed by a human before send.",
    "payment": "Payments require human approval before execution.",
    "travel_booking": "Travel bookings require human approval before purchase or confirmation.",
    "expense_approval": "Expense approvals require human approval before posting.",
    "contract_change": "Contract changes require human approval before commitment.",
    "confidential_document_sharing": "Confidential document sharing requires human approval.",
    "file_deletion": "File deletion requires human approval and must never run automatically.",
    "legal_compliance_decision": "Legal or compliance decisions require human review before action.",
    "emergency_safety_decision": "Emergency or safety decisions require a human decision before action.",
    "policy_exception": "Policy exceptions require human review before action.",
}

HUMAN_DECISION_ACTIONS = {
    "legal_compliance_decision",
    "emergency_safety_decision",
    "policy_exception",
}

ACTION_KEYWORDS = {
    "external_vendor_email": [
        "external vendor email",
        "vendor follow-up",
        "vendor follow up",
        "email the vendor",
        "send to vendor",
        "follow up externally",
        "vendor review meeting",
    ],
    "payment": ["payment", "pay invoice", "wire transfer", "send money", "release funds"],
    "travel_booking": ["travel booking", "book travel", "book flight", "book hotel", "reserve flight"],
    "expense_approval": ["expense approval", "approve expense", "reimbursement", "expense report"],
    "contract_change": [
        "contract change",
        "change contract",
        "contract amendment",
        "approve expansion",
        "terminate contract",
    ],
    "confidential_document_sharing": [
        "confidential document",
        "share confidential",
        "sensitive file",
        "restricted document",
    ],
    "file_deletion": ["delete file", "delete files", "remove file", "remove files", "destroy file"],
    "legal_compliance_decision": ["legal decision", "compliance decision", "legal/compliance"],
    "emergency_safety_decision": ["emergency", "safety decision", "evacuate", "fire alarm", "gas alarm"],
    "policy_exception": ["policy exception", "override policy", "exception to policy"],
}


AUTO_ALLOWED_ACTIONS = {
    "calendar_hold",
    "agenda_preparation",
    "internal_reminder",
    "meeting_notes",
    "task_creation",
    "dashboard_update",
}


def requires_approval(action_type: str) -> bool:
    return action_type in APPROVAL_REASONS


def approval_reason(action_type: str) -> str | None:
    return APPROVAL_REASONS.get(action_type)


def can_auto_execute(action_type: str) -> bool:
    return action_type in AUTO_ALLOWED_ACTIONS


def detect_approval_actions(text: str) -> list[str]:
    normalized = text.lower()
    matches = []
    for action_type, keywords in ACTION_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            matches.append(action_type)
    return matches


def safety_review(text: str) -> dict:
    actions = detect_approval_actions(text)
    if not actions:
        return {
            "approval_required": False,
            "approval_reason": "",
            "human_decision_required": False,
            "risk_level": "low",
            "matched_actions": [],
        }

    human_decision_required = any(action in HUMAN_DECISION_ACTIONS for action in actions)
    reasons = [APPROVAL_REASONS[action] for action in actions]
    risk_level = "critical" if "emergency_safety_decision" in actions else "high"
    if actions == ["external_vendor_email"]:
        risk_level = "medium"

    return {
        "approval_required": True,
        "approval_reason": " ".join(reasons),
        "human_decision_required": human_decision_required,
        "risk_level": risk_level,
        "matched_actions": actions,
    }
