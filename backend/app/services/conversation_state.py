from __future__ import annotations

from typing import Any

# In-memory store keyed by user_id. Lives for the process lifetime.
_conversation_store: dict[int | str, "ConversationState"] = {}

REQUIRED_FIELDS: dict[str, list[str]] = {
    "create_ticket":        ["title", "category", "priority", "branch"],
    "create_task":          ["title", "category", "priority", "assigned_to"],
    "approve_expense":      ["expense_id", "action"],
    "ticket_status_update": ["ticket_id", "status"],
}

FIELD_PROMPTS: dict[str, str] = {
    "title":       "What should the title be?",
    "category":    "What category? (e.g. Hardware, Software, General)",
    "priority":    "What priority? (Low / Medium / High)",
    "branch":      "Which branch? (Pune / Ahmedabad / Vadodara / Noida)",
    "assigned_to": "Who should this be assigned to?",
    "ticket_id":   "What is the ticket ID? (e.g. IT-1001)",
    "status":      "What status? (e.g. Resolved, Closed, In Progress)",
    "expense_id":  "What is the expense ID? (e.g. EXP-1001)",
    "action":      "Approve or Reject?",
}


class ConversationState:
    def __init__(self, intent: str, required_fields: list[str], entities: dict[str, Any]):
        self.intent = intent
        self.required_fields = required_fields
        self.collected: dict[str, Any] = {
            k: v for k, v in entities.items() if v not in (None, "", [])
        }
        self.pending_confirmation = False

    def next_missing_field(self) -> str | None:
        for field in self.required_fields:
            if not self.collected.get(field):
                return field
        return None

    def is_complete(self) -> bool:
        return self.next_missing_field() is None

    def collect(self, field: str, value: Any) -> None:
        self.collected[field] = value

    def prompt_for(self, field: str) -> str:
        return FIELD_PROMPTS.get(field, f"What is the **{field}**?")


def get_state(user_id: int | str) -> ConversationState | None:
    return _conversation_store.get(user_id)


def set_state(user_id: int | str, state: ConversationState) -> None:
    _conversation_store[user_id] = state


def clear_state(user_id: int | str) -> None:
    _conversation_store.pop(user_id, None)
