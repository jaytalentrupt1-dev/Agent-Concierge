from __future__ import annotations

import re

from app.repositories.admin_repository import AdminRepository
from app.services.conversation_state import (
    REQUIRED_FIELDS,
    ConversationState,
    clear_state,
    get_state,
    set_state,
)
from app.services.tool_executor import ToolExecutor

_CONFIRM_PHRASES = frozenset({"yes", "confirm", "ok", "sure", "proceed", "y", "yep", "yeah"})
_CANCEL_PHRASES = frozenset({"no", "cancel", "n", "stop", "abort", "nope"})

# Intents already handled by chatbot_agent_response_for in main.py.
# Do NOT intercept fresh occurrences of these — let existing logic run.
# Ongoing conversation state (slot-filling continuation) still overrides.
#
# NOTE: "create_ticket" is intentionally NOT in this set. Bare "create a ticket"
# commands are handled here with step-by-step slot-filling. Rich requests that
# contain a description (e.g. "create ticket for laptop issue") fall through to
# chatbot_create_ticket_from_text via _is_bare_ticket_request() below.
_HANDLED_BY_EXISTING_CODE = frozenset({
    "create_task",
    "create_vendor",
    "ticket_status_update",
    "ticket_status",
})

# Words that contribute no descriptive content to a ticket creation request.
# Used to distinguish "create a ticket" (bare) from "create ticket for laptop issue" (rich).
_BARE_TICKET_WORDS = frozenset({
    "create", "raise", "open", "new", "ticket", "tickets",
    "a", "an", "the", "please", "me", "i", "want", "need", "to",
})


def _is_bare_ticket_request(message: str) -> bool:
    """Return True when the message is a bare create-ticket command with no description.

    "create a ticket"            → True  (bare, start slot-filling)
    "raise a ticket"             → True
    "create tikcet for laptop issue" → False  (has content, let existing code handle)
    "create ticket hardware broken"  → False
    """
    words = set(re.sub(r"[^a-z\s]", "", message.strip().lower()).split())
    content_words = words - _BARE_TICKET_WORDS
    return len(content_words) <= 1


class ActionHandler:
    """Bridges intent → slot-filling conversation → confirmation → execution."""

    def __init__(self, repository: AdminRepository, current_user: dict):
        self.executor = ToolExecutor(repository, current_user)
        self.user_id = current_user.get("id")
        self._current_user = current_user

    def handle(self, message: str, intent_result: dict) -> str | None:
        """Return a response string, or None to fall through to the existing Conci logic."""
        intent = intent_result.get("intent", "unsupported")
        entities = dict(intent_result.get("entities") or {})
        action_type = intent_result.get("action_type", "answer")
        confirmation_required = bool(intent_result.get("confirmation_required", False))

        cleaned = message.strip().lower()
        state = get_state(self.user_id)

        # ── Waiting for confirmation (ongoing state always takes priority) ──────
        if state and state.pending_confirmation:
            if cleaned in _CONFIRM_PHRASES:
                result = self.executor.execute(state.intent, state.collected)
                clear_state(self.user_id)
                response = self._format_result(result)
                self._maybe_notify_telegram(state.intent, result)
                return response
            if cleaned in _CANCEL_PHRASES or intent == "unsupported":
                clear_state(self.user_id)
                return "Action cancelled. How else can I help?"
            # Any other message restarts — fall through so Conci handles it
            clear_state(self.user_id)
            return None

        # ── Active slot-filling state ───────────────────────────────────────────
        if state and not state.is_complete():
            # If the user sent a recognized new intent instead of a field value,
            # abort the old flow and let the new intent be handled normally.
            if intent != "unsupported" and intent != state.intent:
                clear_state(self.user_id)
                return None

            field = state.next_missing_field()
            state.collect(field, message.strip())
            set_state(self.user_id, state)

            next_field = state.next_missing_field()
            if next_field:
                return f"Got it. {state.prompt_for(next_field)}"

            # All fields collected — check if confirmation needed
            if confirmation_required or state.intent in ("ticket_status_update", "approve_expense"):
                state.pending_confirmation = True
                set_state(self.user_id, state)
                return self._confirmation_prompt(state)

            result = self.executor.execute(state.intent, state.collected)
            clear_state(self.user_id)
            response = self._format_result(result)
            self._maybe_notify_telegram(state.intent, result)
            return response

        # ── New create / update intent ──────────────────────────────────────────
        # Skip intents already handled by chatbot_agent_response_for so that
        # existing behavior (task/vendor creation, status updates) is preserved.
        if intent in _HANDLED_BY_EXISTING_CODE:
            return None

        # ── create_ticket: smart routing ────────────────────────────────────────
        # Rich requests ("create ticket for laptop issue") contain a description
        # that chatbot_create_ticket_from_text can auto-create from.
        # Bare requests ("create a ticket") have no content → use slot-filling.
        if intent == "create_ticket" and action_type == "create":
            if not _is_bare_ticket_request(message):
                # Has description content — fall through to chatbot_create_ticket_from_text
                return None
            # Bare request — start step-by-step slot-filling
            required = REQUIRED_FIELDS.get("create_ticket", [])
            new_state = ConversationState("create_ticket", required, entities)
            set_state(self.user_id, new_state)
            first = new_state.next_missing_field()
            return f"Sure, let's create a ticket. {new_state.prompt_for(first)}"

        if action_type in ("create", "update"):
            required = REQUIRED_FIELDS.get(intent, [])
            missing = [f for f in required if not entities.get(f)]

            if missing:
                new_state = ConversationState(intent, required, entities)
                set_state(self.user_id, new_state)
                first = new_state.next_missing_field()
                action_label = intent.replace("_", " ")
                return f"I'll help you {action_label}. {new_state.prompt_for(first)}"

            # All required fields already present
            if confirmation_required or intent in ("ticket_status_update", "approve_expense"):
                new_state = ConversationState(intent, required, entities)
                new_state.pending_confirmation = True
                set_state(self.user_id, new_state)
                return self._confirmation_prompt(new_state)

            result = self.executor.execute(intent, entities)
            response = self._format_result(result)
            self._maybe_notify_telegram(intent, result)
            return response

        # Fetch intents fall through to existing Conci AI logic, which has
        # richer formatting, role-scoped source labels, and branch filtering.
        return None

    # ── Telegram notification ────────────────────────────────────────────────────

    def _maybe_notify_telegram(self, intent: str, result: dict) -> None:
        """Send a Telegram notification after successful ticket creation."""
        if intent != "create_ticket":
            return
        if result.get("error"):
            return
        ticket = result.get("ticket", {})
        if not ticket:
            return
        try:
            from app.services.telegram_service import send_telegram_sync
            user = self._current_user
            text = (
                f"🎫 <b>New Ticket Created</b>\n"
                f"ID: {ticket.get('ticket_id', '—')}\n"
                f"Title: {ticket.get('title', '—')}\n"
                f"Category: {ticket.get('category', '—')}\n"
                f"Priority: {ticket.get('priority', '—')}\n"
                f"By: {user.get('name', user.get('email', '—'))}"
            )
            tg = send_telegram_sync(text)
            if not tg.get("ok"):
                import logging
                logging.getLogger(__name__).warning(
                    "create_ticket Telegram notify failed: %s", tg.get("error")
                )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Telegram notify error: %s", exc)

    # ── Formatting ──────────────────────────────────────────────────────────────

    def _confirmation_prompt(self, state: ConversationState) -> str:
        action_label = state.intent.replace("_", " ")
        lines = [f"Ready to **{action_label}**:"]
        for k, v in state.collected.items():
            lines.append(f"• {k}: {v}")
        lines.append("\nConfirm? (yes / no)")
        return "\n".join(lines)

    def _format_result(self, result: dict) -> str:
        if result.get("error"):
            return f"❌ {result['error']}"

        if result.get("message"):
            return f"✅ {result['message']}"

        if "tickets" in result:
            tickets = result["tickets"]
            if not tickets:
                return "No tickets found."
            lines = [f"Found **{result['count']}** ticket(s):\n"]
            for t in tickets[:10]:
                lines.append(
                    f"• **{t.get('ticket_id', t.get('id', ''))}** — {t.get('title', '')} "
                    f"[{t.get('status', '')}] [{t.get('priority', '')}]"
                )
            return "\n".join(lines)

        if "ticket" in result:
            t = result["ticket"]
            if not t:
                return "Ticket not found."
            return (
                f"**{t.get('ticket_id', '')}** — {t.get('title', '')}\n"
                f"Status: {t.get('status', '')} | Priority: {t.get('priority', '')} | "
                f"Category: {t.get('category', '')}"
            )

        if "tasks" in result:
            tasks = result["tasks"]
            if not tasks:
                return "No tasks found."
            lines = [f"Found **{result['count']}** task(s):\n"]
            for t in tasks[:10]:
                lines.append(
                    f"• **{t.get('task_id', t.get('id', ''))}** — {t.get('title', '')} "
                    f"[{t.get('status', '')}] [{t.get('priority', '')}]"
                )
            return "\n".join(lines)

        if "expenses" in result:
            expenses = result["expenses"]
            if not expenses:
                return "No expenses found."
            lines = [f"Found **{result['count']}** expense(s):\n"]
            for ex in expenses[:10]:
                lines.append(
                    f"• **{ex.get('expense_id', ex.get('id', ''))}** — "
                    f"₹{float(ex.get('amount', 0)):,.0f} "
                    f"[{ex.get('status', '')}] {ex.get('category', '')}"
                )
            if result.get("total_amount"):
                lines.append(f"\n**Total: ₹{result['total_amount']:,.0f}**")
            return "\n".join(lines)

        if "items" in result:
            items = result["items"]
            if not items:
                return "No inventory items found."
            lines = [f"Inventory — **{result['count']}** item(s):\n"]
            for i in items[:10]:
                lines.append(
                    f"• {i.get('item_name', i.get('model', ''))} "
                    f"[{i.get('status', '')}] — {i.get('assigned_to', 'Unassigned')}"
                )
            if result.get("alert"):
                lines.append("\n⚠️ Some items are at or below minimum stock level.")
            return "\n".join(lines)

        if "vendors" in result:
            vendors = result["vendors"]
            if not vendors:
                return "No vendors found."
            lines = [f"Found **{result['count']}** vendor(s):\n"]
            for v in vendors[:10]:
                lines.append(
                    f"• **{v.get('vendor_name', '')}** — {v.get('service_provided', '')} "
                    f"[{v.get('status', '')}]"
                )
            if result.get("total_monthly_billing"):
                lines.append(f"\n**Total monthly billing: ₹{result['total_monthly_billing']:,.0f}**")
            return "\n".join(lines)

        if "open_tickets" in result:
            r = result
            return (
                "📊 **Dashboard Summary**\n"
                f"• Open Tickets: {r['open_tickets']}\n"
                f"• Open Tasks: {r['open_tasks']}\n"
                f"• Overdue Tasks: {r['overdue_tasks']}\n"
                f"• Pending Expenses: {r['pending_expenses']}\n"
                f"• Active Vendors: {r['active_vendors']}\n"
                f"• Total Inventory: {r['inventory_total']}"
            )

        return str(result)
