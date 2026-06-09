"""Telegram inline keyboard helpers — Phase C.2.

Each function returns a dict that can be passed directly as the
reply_markup field in a Telegram sendMessage / editMessageText call.

Callback data format (must stay under Telegram's 64-byte limit):
  "exp:approve:{expense_id}"   e.g. "exp:approve:EXP-1001"  (22 bytes max)
  "exp:reject:{expense_id}"    e.g. "exp:reject:EXP-1001"   (21 bytes max)
  "tkt:close:{ticket_id}"      e.g. "tkt:close:IT-1013"     (18 bytes max)
  "cancel:{entity_id}"         e.g. "cancel:EXP-1001"       (16 bytes max)
"""
from __future__ import annotations


def expense_approval_keyboard(expense_id: str) -> dict:
    """Inline keyboard with Approve, Reject, and Cancel buttons for an expense."""
    eid = str(expense_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"exp:approve:{eid}"},
                {"text": "❌ Reject",  "callback_data": f"exp:reject:{eid}"},
            ],
            [
                {"text": "🚫 Cancel", "callback_data": f"cancel:{eid}"},
            ],
        ]
    }


def ticket_close_keyboard(ticket_id: str) -> dict:
    """Inline keyboard with Close and Cancel buttons for a ticket."""
    tid = str(ticket_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Close Ticket", "callback_data": f"tkt:close:{tid}"},
                {"text": "🚫 Cancel",       "callback_data": f"cancel:{tid}"},
            ],
        ]
    }


def task_done_keyboard(task_id: str) -> dict:
    """Inline keyboard with Mark Done and Cancel buttons for a task."""
    tid = str(task_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Mark Done", "callback_data": f"task:done:{tid}"},
                {"text": "🚫 Cancel",    "callback_data": f"cancel:{tid}"},
            ],
        ]
    }


def remove_keyboard() -> dict:
    """Empty reply_markup to strip buttons from an edited message."""
    return {"inline_keyboard": []}


def parse_callback_data(data: str) -> tuple[str, str, str]:
    """Parse a callback_data string into (prefix, action, entity_id).

    Examples:
      "exp:approve:EXP-1001" -> ("exp", "approve", "EXP-1001")
      "exp:reject:EXP-1001"  -> ("exp", "reject",  "EXP-1001")
      "tkt:close:IT-1013"    -> ("tkt", "close",   "IT-1013")
      "cancel:EXP-1001"      -> ("cancel", "",     "EXP-1001")
    """
    parts = data.split(":", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return data, "", ""
