from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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

# Intents that represent an unambiguous new command and should therefore abort
# any active slot-filling conversation.  Only clear-cut fetch lookups and
# different create/update pivots belong here.
#
# NOT included: casual_identity, utility_date, utility_time, file_reading —
# these are too short or generic to reliably distinguish from a slot answer.
# Also NOT included: the intent currently being collected (state.intent) —
# that case is handled by the slot-collection path below.
#
# The core bug this fixes: slot values such as "Laptop screen broken" can
# score ≥ 0.58 against fetch phrases like "inventory summary", triggering the
# old broad abort guard and wiping the ticket-creation state.  The whitelist
# ensures only genuine command-pivots clear the state.
_SLOT_ABORT_INTENTS = frozenset({
    # ── Ticket lookups ─────────────────────────────────────────────────────
    "open_tickets",
    "my_tickets",
    "recent_tickets",
    "ticket_status",
    "ticket_status_update",
    # ── Task lookups ───────────────────────────────────────────────────────
    "open_tasks",
    "my_tasks",
    "overdue_tasks",
    # ── Approval / finance lookups ─────────────────────────────────────────
    "pending_approvals",
    "vendor_billing",
    "active_vendors",
    "vendor_count",
    "vendor_details",
    "pending_expenses",
    "expenses_by_month",
    "expenses_by_category",
    "expenses_last_month",
    "expenses_this_month",
    # ── Inventory lookups ──────────────────────────────────────────────────
    "inventory_summary",
    "inventory_in_use",
    "inventory_submitted_vendor",
    "inventory_recent_updates",
    # ── Travel / calendar ─────────────────────────────────────────────────
    "travel_spend",
    "travel_recent_records",
    "calendar_events",
    # ── Reports / admin ───────────────────────────────────────────────────
    "reports",
    "users_settings",
    # ── Utility ───────────────────────────────────────────────────────────
    "help",
    # ── Clearly different create/update flows ──────────────────────────────
    "create_ticket",   # restart a ticket flow (distinct from collecting a slot value)
    "create_task",
    "create_vendor",
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
            # Any other message during confirmation — clear state and fall through
            logger.debug(
                "Conci slot-filling aborted: unexpected message during confirmation "
                "(state.intent=%s, user_id=%s)",
                state.intent, self.user_id,
            )
            clear_state(self.user_id)
            return None

        # ── Active slot-filling state ───────────────────────────────────────────
        if state and not state.is_complete():
            # Only abort when the user sends an unambiguous new command.
            #
            # Two guards work together:
            #   1. Whitelist — only fetch lookups and clearly different create/update
            #      flows can abort.  Generic slot values like "Medium" or "IT" will
            #      return "unsupported" and never reach this branch at all.
            #   2. Confidence floor (≥ 0.85) — prevents descriptive slot values like
            #      "Laptop screen broken" (fuzzy score ≈ 0.58–0.65 against phrases
            #      such as "device summary") from triggering a false abort.  Only
            #      high-confidence matches (strong-rule 0.96, OpenAI 0.9) qualify.
            #
            # This replaces the old guard (`intent != "unsupported" and
            # intent != state.intent`) which aborted on ANY classifier hit ≥ 0.58.
            confidence = float(intent_result.get("confidence") or 0.0)
            source = intent_result.get("classification_source", "local")
            # "ai" source means OpenAI/DeepInfra classified the intent.  We do NOT
            # abort slot-filling on AI-only confidence because the typo-corrector
            # can corrupt slot values before they reach the model, causing false pivots
            # (e.g. "filling"→"billing" → AI fires vendor_billing at 0.9, clearing the state).
            # Only "strong_rule" (keyword rules, 0.96) and "local" (phrase similarity,
            # confirmed ≥ 0.85 by the score) are trusted to abort an active flow.
            _will_abort = (
                intent in _SLOT_ABORT_INTENTS
                and intent != state.intent
                and confidence >= 0.85
                and source != "ai"
            )
            logger.info(
                "SLOT DEBUG | input=%r | detected_intent=%s | confidence=%.3f"
                " | source=%s | state.intent=%s | in_whitelist=%s | abort_decision=%s",
                message,
                intent,
                confidence,
                source,
                state.intent,
                intent in _SLOT_ABORT_INTENTS,
                _will_abort,
            )
            if _will_abort:
                logger.debug(
                    "Conci slot-filling aborted: user pivoted to intent=%s "
                    "(confidence=%.2f) mid-flow (state.intent=%s, user_id=%s)",
                    intent, confidence, state.intent, self.user_id,
                )
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
