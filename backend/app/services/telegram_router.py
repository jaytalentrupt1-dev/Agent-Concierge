"""Telegram Phase B / C.1 / C.2 / C.3 — Query router + write intents.

Phase B:   Read intents classified, fetched via ToolExecutor, formatted as HTML.
Phase C.1: create_ticket via guided slot-filling + PIN gate.
Phase C.2: approve/reject expense + close ticket via inline buttons + PIN gate.
Phase C.3: PIN verification layer; create_task slot-filling; mark_task_done;
           update_ticket status / assign.

All errors are caught — never raises to the caller.
Uses HTML parse mode throughout.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# ── Telegram character limit ──────────────────────────────────────────────────
_TG_MAX_CHARS = 4096

# ── Intent classification buckets ────────────────────────────────────────────

# Intents the bot will answer (mapped to a data-fetch + format flow)
_READ_INTENTS: frozenset[str] = frozenset({
    # Tickets
    "open_tickets", "my_tickets", "recent_tickets", "ticket_status",
    # Tasks
    "open_tasks", "my_tasks", "overdue_tasks",
    # Approvals / expenses
    "pending_approvals", "pending_expenses", "expense_summary",
    "expenses_by_month", "expenses_by_category", "expenses_last_month", "expenses_this_month",
    # Vendors
    "active_vendors", "vendor_billing", "vendor_count", "vendor_details",
    # Inventory
    "inventory_summary", "inventory_in_use", "inventory_submitted_vendor", "inventory_recent_updates",
    # Travel
    "travel_spend", "travel_recent_records",
    # Utility
    "help", "casual_identity", "utility_date", "utility_time",
    # Internal sentinel for "daily_summary" (triggered by /summary command or natural lang)
    "daily_summary",
})

# Intents that would mutate data and are NOT yet handled.
# create_ticket → Phase C.1 (slot-filling), approve_expense / ticket_status_update → Phase C.2.
# create_task / mark_task_done / update_ticket → Phase C.3 (handled below).
_WRITE_INTENTS: frozenset[str] = frozenset({
    "create_vendor",
})

# Phrases that identify a bare create-ticket request (no title embedded)
_CREATE_TICKET_PHRASES: tuple[str, ...] = (
    "create ticket", "create a ticket", "raise ticket", "raise a ticket",
    "new ticket", "open ticket", "open a ticket", "create new ticket",
    "make ticket", "make a ticket", "add ticket",
)

# Slot order for create_ticket — mirrors conversation_state.py
_TICKET_SLOTS: tuple[str, ...] = ("title", "category", "priority", "branch")

_TICKET_SLOT_PROMPTS: dict[str, str] = {
    "title":    "What should the title be?",
    "category": "What category? (e.g. Hardware, Software, General)",
    "priority": "What priority? (Low / Medium / High)",
    "branch":   "Which branch? (Pune / Ahmedabad / Vadodara / Noida)",
}

_CONFIRM_WORDS: frozenset[str] = frozenset({"yes", "y", "confirm", "ok", "sure", "yep", "yeah"})
_CANCEL_WORDS:  frozenset[str] = frozenset({"no", "n", "cancel", "nope", "abort", "stop"})

# Regex patterns for text-based approval / close triggers (Phase C.2)
_RE_APPROVE = re.compile(
    r"(?:approve|accept)\s+(?:(?:expense|exp)\s+)?#?([A-Za-z0-9-]+)",
    re.IGNORECASE,
)
_RE_REJECT = re.compile(
    r"(?:reject|deny|decline)\s+(?:(?:expense|exp)\s+)?#?([A-Za-z0-9-]+)",
    re.IGNORECASE,
)
_RE_CLOSE = re.compile(
    r"(?:close|resolve)\s+(?:(?:ticket|tkt)\s+)?#?([A-Za-z0-9-]+)",
    re.IGNORECASE,
)

# ── Phase C.3 write-intent regex patterns ─────────────────────────────────────

_RE_MARK_DONE = re.compile(
    r"(?:mark|set|complete|finish|done)\s+(?:task\s+)?#?([A-Za-z0-9-]+)\s+(?:as\s+)?(?:done|complete|completed|finished)",
    re.IGNORECASE,
)
_RE_UPDATE_TICKET_STATUS = re.compile(
    r"(?:update|set|change)\s+(?:ticket\s+)?#?([A-Za-z0-9-]+)\s+(?:status\s+)?(?:to\s+)(open|in\s*progress|closed|resolved|pending)",
    re.IGNORECASE,
)
_RE_ASSIGN_TICKET = re.compile(
    r"assign\s+(?:ticket\s+)?#?([A-Za-z0-9-]+)\s+to\s+(admin|it_manager|it manager)",
    re.IGNORECASE,
)

# Slot config for create_task
_TASK_SLOTS: tuple[str, ...] = ("title", "assigned_role", "due_date")
_TASK_SLOT_PROMPTS: dict[str, str] = {
    "title":         "What should the task title be?",
    "assigned_role": "Assign to which role? (admin / it_manager)",
    "due_date":      "Due date? (e.g. 2026-06-20)\n\n<i>Or send /skip to use 7 days from today.</i>",
}
_CREATE_TASK_PHRASES: tuple[str, ...] = (
    "create task", "create a task", "new task", "add task", "make task",
    "make a task", "add a task", "create new task",
)

# Phrases that trigger the daily_summary shortcut before classifying
_SUMMARY_PHRASES = (
    "daily summary", "today's summary", "todays summary",
    "what's today", "whats today", "morning briefing", "briefing",
    "status update", "what happened today",
)

_HELP_TEXT = (
    "🤔 <b>Here's what I can do:</b>\n\n"
    "🎫 <i>Ticket queries</i>\n"
    "  • show open tickets\n"
    "  • my tickets\n"
    "  • recent tickets\n\n"
    "✅ <i>Task queries</i>\n"
    "  • open tasks\n"
    "  • my tasks\n"
    "  • overdue tasks\n\n"
    "💰 <i>Finance queries</i>\n"
    "  • pending approvals\n"
    "  • pending expenses\n"
    "  • active vendors\n"
    "  • vendor billing\n\n"
    "📦 <i>Inventory queries</i>\n"
    "  • inventory summary\n\n"
    "📊 <i>Dashboard</i>\n"
    "  • /summary — today's snapshot\n\n"
    "✏️ <i>Create / Actions</i>\n"
    "  • create ticket — guided ticket creation\n"
    "  • create task — guided task creation\n"
    "  • approve expense EXP-001 — approve with buttons\n"
    "  • reject expense EXP-001 — reject with buttons\n"
    "  • close ticket IT-1001 — close with confirmation\n"
    "  • mark task TASK-001 done — mark task complete\n"
    "  • update ticket IT-001 to In Progress\n\n"
    "ℹ️ <i>Commands</i>\n"
    "  /help /summary /cancel /whoami /unregister"
)

# ── HTML helpers ──────────────────────────────────────────────────────────────

def _e(value: Any) -> str:
    """HTML-escape a string for Telegram HTML parse mode."""
    s = str(value or "")
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s


def _truncate(items: list[str], limit: int = 10) -> tuple[list[str], int]:
    """Return (first-N items, how many were cut)."""
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


# ── Telegram send helper (HTML mode) ─────────────────────────────────────────

def _tg_post_html(token: str, chat_id: int, text: str) -> None:
    """Send an HTML-mode message. Never raises."""
    url = _TELEGRAM_API.format(token=token, method="sendMessage")
    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        ensure_ascii=False,
    ).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if not result.get("ok"):
            logger.warning("Telegram send failed: %s", result.get("description"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram send error: %s", exc)


def _send(token: str, chat_id: int, text: str) -> None:
    """Send text, splitting at TG_MAX_CHARS boundaries if needed."""
    if not text:
        return
    if len(text) <= _TG_MAX_CHARS:
        _tg_post_html(token, chat_id, text)
        return
    # Split at newline boundaries to avoid cutting in the middle of a line
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = current + "\n" + line if current else line
        if len(candidate) > _TG_MAX_CHARS:
            if current:
                parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    for part in parts:
        _tg_post_html(token, chat_id, part)


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_tickets(data: dict, intent: str) -> str:
    tickets = data.get("tickets", [])
    if not tickets:
        return "✨ No tickets found. You're all caught up."

    label_map = {
        "my_tickets": "Your Tickets",
        "recent_tickets": "Recent Tickets",
        "open_tickets": "Open Tickets",
        "ticket_status": "Ticket Status",
    }
    label = label_map.get(intent, "Tickets")
    shown, cut = _truncate(tickets)

    lines = [f"<b>🎫 {_e(label)} ({len(tickets)})</b>\n"]
    for t in shown:
        tid = _e(t.get("ticket_id", t.get("id", "?")))
        title = _e(t.get("title", "—"))
        priority = _e(t.get("priority", ""))
        status = _e(t.get("status", ""))
        branch = _e(t.get("branch", ""))
        lines.append(f"• <code>{tid}</code> — {title}")
        if priority or status:
            lines.append(f"  <i>{status}</i> · {priority}" + (f" · {branch}" if branch else ""))
    if cut:
        lines.append(f"\n<i>...and {cut} more. Open the web app to see all.</i>")
    else:
        lines.append("\n<i>Open the web app for full details.</i>")
    return "\n".join(lines)


def _fmt_tasks(data: dict, intent: str) -> str:
    tasks = data.get("tasks", [])
    if not tasks:
        return "✨ No tasks found. You're all caught up."

    label_map = {
        "my_tasks": "Your Tasks",
        "overdue_tasks": "⚠️ Overdue Tasks",
        "open_tasks": "Open Tasks",
    }
    label = label_map.get(intent, "Tasks")
    shown, cut = _truncate(tasks)

    lines = [f"<b>✅ {_e(label)} ({len(tasks)})</b>\n"]
    for t in shown:
        tid = _e(t.get("task_id", t.get("id", "?")))
        title = _e(t.get("title", "—"))
        priority = _e(t.get("priority", ""))
        assigned = _e(t.get("assigned_to", ""))
        due = str(t.get("due_date", ""))[:10]
        lines.append(f"• <code>{tid}</code> — {title}")
        meta = " · ".join(filter(None, [priority, f"@{assigned}" if assigned else "", f"due {due}" if due else ""]))
        if meta:
            lines.append(f"  <i>{meta}</i>")
    if cut:
        lines.append(f"\n<i>...and {cut} more. Open the web app to see all.</i>")
    else:
        lines.append("\n<i>Open the web app for full details.</i>")
    return "\n".join(lines)


def _fmt_expenses(data: dict, intent: str) -> str:
    expenses = data.get("expenses", [])
    if not expenses:
        return "✨ No expenses found."

    label_map = {
        "pending_expenses": "Pending Expenses",
        "pending_approvals": "Pending Approvals",
        "expense_summary": "Expense Summary",
        "expenses_by_month": "Monthly Expenses",
        "expenses_by_category": "Expenses by Category",
        "expenses_last_month": "Last Month Expenses",
        "expenses_this_month": "This Month Expenses",
    }
    label = label_map.get(intent, "Expenses")
    shown, cut = _truncate(expenses)
    total = data.get("total_amount") or sum(float(e.get("amount", 0)) for e in expenses)

    lines = [f"<b>💰 {_e(label)} ({len(expenses)})</b>\n"]
    for ex in shown:
        eid = _e(ex.get("expense_id", ex.get("id", "?")))
        amount = f"₹{float(ex.get('amount', 0)):,.0f}"
        category = _e(ex.get("category", ""))
        status = _e(ex.get("status", ""))
        lines.append(f"• <code>{eid}</code> — {amount}" + (f" — {category}" if category else ""))
        if status:
            lines.append(f"  <i>{status}</i>")
    if total:
        lines.append(f"\n<b>Total: ₹{total:,.0f}</b>")
    if cut:
        lines.append(f"<i>...and {cut} more. Open the web app to see all.</i>")
    if intent in ("pending_expenses", "pending_approvals"):
        lines.append("\n<i>To approve: send <b>approve expense &lt;id&gt;</b></i>")
    return "\n".join(lines)


def _fmt_vendors(data: dict, intent: str) -> str:
    vendors = data.get("vendors", [])
    if not vendors:
        return "✨ No vendors found."

    label = "Active Vendors" if intent in ("active_vendors", "vendor_list") else "Vendors"
    if intent == "vendor_billing":
        label = "Vendor Billing"
    shown, cut = _truncate(vendors)
    total_billing = data.get("total_monthly_billing")

    lines = [f"<b>🏢 {_e(label)} ({len(vendors)})</b>\n"]
    for v in shown:
        name = _e(v.get("vendor_name", "—"))
        service = _e(v.get("service_provided", ""))
        if intent == "vendor_billing":
            amount = f"₹{float(v.get('billing_amount', 0)):,.0f}"
            cycle = _e(v.get("billing_cycle", ""))
            lines.append(f"• {name} — {amount}/{cycle}")
        else:
            lines.append(f"• {name}" + (f" — {service}" if service else ""))
    if total_billing:
        lines.append(f"\n<b>Monthly total: ₹{total_billing:,.0f}</b>")
    if cut:
        lines.append(f"<i>...and {cut} more. Open the web app to see all.</i>")
    else:
        lines.append(f"\n<i>Total: {len(vendors)}</i>")
    return "\n".join(lines)


def _fmt_inventory(data: dict, intent: str) -> str:
    items = data.get("items", [])
    if not items:
        return "✨ No inventory items found."

    label_map = {
        "inventory_summary": "Inventory Summary",
        "inventory_in_use": "Inventory In Use",
        "inventory_submitted_vendor": "Submitted to Vendor",
        "inventory_recent_updates": "Recent Inventory Updates",
    }
    label = label_map.get(intent, "Inventory")
    shown, cut = _truncate(items)

    lines = [f"<b>📦 {_e(label)} ({len(items)})</b>\n"]
    for item in shown:
        name = _e(item.get("item_name") or item.get("model_no") or item.get("model") or "—")
        serial = _e(item.get("serial_no") or item.get("serial_number") or "")
        status = _e(item.get("status", ""))
        assigned = _e(item.get("employee_name") or item.get("assigned_to") or "")
        lines.append(f"• {name}" + (f" [{serial}]" if serial else ""))
        meta = " · ".join(filter(None, [status, f"→ {assigned}" if assigned else ""]))
        if meta:
            lines.append(f"  <i>{meta}</i>")
    if data.get("alert"):
        lines.append("\n⚠️ <i>Some items are below minimum stock level.</i>")
    if cut:
        lines.append(f"\n<i>...and {cut} more. Open the web app to see all.</i>")
    return "\n".join(lines)


def _fmt_daily_summary(user: dict, database_path: str) -> str:
    """Build a role-aware daily summary message."""
    from app.repositories.admin_repository import AdminRepository
    repo = AdminRepository(database_path)
    role = user.get("role", "")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        tickets = repo.list_tickets()
        tasks = repo.list_tasks()
        expenses = repo.list_expenses()
    except Exception as exc:  # noqa: BLE001
        logger.warning("daily_summary fetch error: %s", exc)
        return "⚠️ Could not load summary data. Try again shortly."

    today = datetime.now(timezone.utc).date().isoformat()

    open_tickets = [t for t in tickets if t.get("status", "").lower() == "open"]
    overdue_tickets = [t for t in tickets if t.get("status", "").lower() == "overdue"]
    overdue_tasks = [
        t for t in tasks
        if t.get("status", "").lower() not in ("completed", "cancelled", "closed")
        and t.get("due_date") and str(t.get("due_date", "")) < today
    ]
    open_tasks = [t for t in tasks if t.get("status", "").lower() == "open"]
    pending_expenses = [
        ex for ex in expenses
        if ex.get("status", "").lower() in ("pending approval", "pending_approval")
    ]

    lines = [f"<b>📊 Today's Summary</b>\n"]

    if role in ("admin",):
        # Admin sees everything
        lines.append(f"🎫 Open Tickets: <b>{len(open_tickets)}</b>" +
                     (f" ({len(overdue_tickets)} overdue)" if overdue_tickets else ""))
        lines.append(f"✅ Open Tasks: <b>{len(open_tasks)}</b>" +
                     (f" ({len(overdue_tasks)} overdue)" if overdue_tasks else ""))
        lines.append(f"💰 Pending Expenses: <b>{len(pending_expenses)}</b>")

    elif role == "it_manager":
        it_open = [t for t in open_tickets if t.get("assigned_role") in ("it_manager",) or t.get("ticket_type", "").lower() == "it"]
        it_overdue = [t for t in overdue_tickets if t.get("ticket_type", "").lower() == "it"]
        lines.append(f"🎫 IT Open Tickets: <b>{len(it_open)}</b>" +
                     (f" ({len(it_overdue)} overdue)" if it_overdue else ""))
        lines.append(f"✅ Open Tasks: <b>{len(open_tasks)}</b>" +
                     (f" ({len(overdue_tasks)} overdue)" if overdue_tasks else ""))

    elif role == "finance_manager":
        lines.append(f"💰 Pending Expenses: <b>{len(pending_expenses)}</b>")
        lines.append(f"🎫 Open Tickets: <b>{len(open_tickets)}</b>")

    else:
        # Employee — only their own
        uid = user.get("id")
        my_tickets = [t for t in open_tickets if t.get("requester_user_id") == uid]
        lines.append(f"🎫 Your Open Tickets: <b>{len(my_tickets)}</b>")
        my_tasks = [t for t in open_tasks
                    if t.get("assigned_user_id") == uid
                    or t.get("assigned_to", "").lower() == (user.get("name", "")).lower()]
        lines.append(f"✅ Your Open Tasks: <b>{len(my_tasks)}</b>")

    lines.append(f"\n<i>Updated: {now_str}</i>")
    return "\n".join(lines)


def _fmt_help(user: dict) -> str:
    role = user.get("role", "")
    role_note = {
        "it_manager": "\n<i>ℹ️ You have IT Manager access — tickets and tasks visible.</i>",
        "finance_manager": "\n<i>ℹ️ You have Finance Manager access — expenses and vendors visible.</i>",
        "employee": "\n<i>ℹ️ You have Employee access — your own tickets and tasks only.</i>",
        "admin": "\n<i>ℹ️ You have Admin access — all data visible.</i>",
    }.get(role, "")
    return _HELP_TEXT + role_note


# ── Phase C.2 — inline button callback + approve/reject/close helpers ────────

def _send_expense_confirmation(
    user: dict,
    expense_id_str: str,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Fetch expense and send a confirmation message with inline buttons."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_buttons import expense_approval_keyboard
    from app.services.telegram_service import send_telegram_with_buttons
    from app.services.telegram_state import PendingConfirmation, set_pending_confirmation

    # Permission check
    if user.get("role") not in ("admin", "finance_manager"):
        _send(token, chat_id, "🔒 You don't have permission to approve or reject expenses.")
        return

    repo = AdminRepository(database_path)
    expense = repo.get_expense_by_expense_id(expense_id_str)
    if not expense:
        _send(token, chat_id, f"❓ Expense <code>{_e(expense_id_str)}</code> not found.")
        return

    amount = f"Rs.{float(expense.get('amount', 0)):,.0f}"
    category = _e(expense.get("category", ""))
    submitted_by = _e(expense.get("employee_name", expense.get("submitted_by", "")))
    status = _e(expense.get("status", ""))
    date_str = str(expense.get("expense_date") or expense.get("created_at") or "")[:10]

    text = (
        f"<b>Approve or reject this expense?</b>\n\n"
        f"<b>ID:</b> {_e(expense_id_str)}\n"
        f"<b>Amount:</b> {amount}\n"
        f"<b>Category:</b> {category}\n"
        f"<b>Submitted by:</b> {submitted_by}\n"
        f"<b>Date:</b> {date_str}\n"
        f"<b>Status:</b> {status}"
    )
    keyboard = expense_approval_keyboard(expense_id_str)
    result = send_telegram_with_buttons(chat_id, text, keyboard)
    if result.get("ok"):
        msg_id = result.get("message_id", 0)
        # Store pending confirmation for typed yes/no fallback
        from app.services.telegram_state import PendingConfirmation, set_pending_confirmation
        set_pending_confirmation(user["id"], PendingConfirmation(
            user_id=user["id"],
            action="approve_expense",   # default; reject uses the button
            entity_id=expense_id_str,
            message_id=msg_id,
        ))
    else:
        logger.warning("Failed to send expense confirmation: %s", result.get("error"))


def _send_ticket_close_confirmation(
    user: dict,
    ticket_id_str: str,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Fetch ticket and send a close confirmation message with inline buttons."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_buttons import ticket_close_keyboard
    from app.services.telegram_service import send_telegram_with_buttons

    if user.get("role") not in ("admin", "it_manager"):
        _send(token, chat_id, "🔒 You don't have permission to close tickets.")
        return

    repo = AdminRepository(database_path)
    # Find by string ID (IT-1013, ADM-1001, etc.)
    tickets = [t for t in repo.list_tickets()
               if t.get("ticket_id", "").upper() == ticket_id_str.upper()]
    if not tickets:
        _send(token, chat_id, f"❓ Ticket <code>{_e(ticket_id_str)}</code> not found.")
        return
    ticket = tickets[0]

    title = _e(ticket.get("title", ""))
    status = _e(ticket.get("status", ""))
    priority = _e(ticket.get("priority", ""))
    branch = _e(ticket.get("branch", ""))
    tid = _e(ticket.get("ticket_id", ticket_id_str))

    text = (
        f"<b>Close this ticket?</b>\n\n"
        f"<b>ID:</b> {tid}\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Priority:</b> {priority}\n"
        f"<b>Branch:</b> {branch}"
    )
    keyboard = ticket_close_keyboard(tid)
    result = send_telegram_with_buttons(chat_id, text, keyboard)
    if result.get("ok"):
        msg_id = result.get("message_id", 0)
        from app.services.telegram_state import PendingConfirmation, set_pending_confirmation
        set_pending_confirmation(user["id"], PendingConfirmation(
            user_id=user["id"],
            action="close_ticket",
            entity_id=tid,
            message_id=msg_id,
        ))
    else:
        logger.warning("Failed to send ticket close confirmation: %s", result.get("error"))


def _execute_action_and_edit(
    action: str,
    entity_id: str,
    message_id: int,
    user: dict,
    chat_id: int,
    database_path: str,
) -> None:
    """Execute an approve/reject/close action and edit the original message."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.tool_executor import ToolExecutor
    from app.services.telegram_buttons import remove_keyboard
    from app.services.telegram_service import edit_telegram_message, send_telegram_sync

    repo = AdminRepository(database_path)
    executor = ToolExecutor(repo, user)

    try:
        if action in ("approve_expense", "reject_expense"):
            approval_action = "Approved" if action == "approve_expense" else "Rejected"
            result = executor.execute("approve_expense", {
                "expense_id": entity_id,
                "action":     approval_action,
            })
            verb = "approved" if action == "approve_expense" else "rejected"
            icon = "✅" if action == "approve_expense" else "❌"
        elif action == "close_ticket":
            result = executor.execute("ticket_status_update", {
                "ticket_id": entity_id,
                "status":    "Closed",
            })
            verb = "closed"
            icon = "✅"
        else:
            logger.warning("Unknown action in _execute_action_and_edit: %s", action)
            return

        if result.get("error"):
            err = _e(str(result["error"]))
            new_text = f"⚠️ Action failed: {err}"
        else:
            new_text = f"{icon} <b>{entity_id} {verb}.</b>"
            # Outbound Telegram alert (same channel as agent alerts)
            try:
                if action in ("approve_expense", "reject_expense"):
                    send_telegram_sync(
                        f"💰 <b>Expense {verb.capitalize()}</b>\n"
                        f"ID: {entity_id}\n"
                        f"By: {user.get('name', user.get('email', ''))}"
                    )
                elif action == "close_ticket":
                    send_telegram_sync(
                        f"🎫 <b>Ticket Closed</b>\n"
                        f"ID: {entity_id}\n"
                        f"By: {user.get('name', user.get('email', ''))}"
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Outbound alert error: %s", exc)

    except Exception as exc:  # noqa: BLE001
        logger.error("_execute_action_and_edit error: %s", exc, exc_info=True)
        new_text = "⚠️ Something went wrong. Please try again or use the web app."

    # Edit original message to show result and remove buttons
    edit_result = edit_telegram_message(chat_id, message_id, new_text, remove_keyboard())
    if not edit_result.get("ok"):
        # Message may be too old to edit — fall back to sending a fresh reply
        logger.debug("edit_telegram_message failed: %s — sending fresh message", edit_result.get("error"))
        _tg_post_html(
            os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id,
            new_text,
        )

    _log_query(database_path, user, action, action, "success" if "failed" not in new_text else "error",
               extra={"entity_id": entity_id, "via": "button_or_typed"})


def handle_callback(
    user: dict,
    callback_data: str,
    message_id: int,
    chat_id: int,
    database_path: str,
) -> None:
    """Handle an inline button click. Called from the listener's callback_query path.

    Always clears the pending confirmation regardless of outcome.
    """
    from app.services.telegram_buttons import parse_callback_data, remove_keyboard
    from app.services.telegram_service import edit_telegram_message
    from app.services.telegram_state import clear_pending_confirmation

    prefix, action, entity_id = parse_callback_data(callback_data)

    logger.info(
        "Telegram callback | user=%s | prefix=%s | action=%s | entity=%s",
        user.get("email"), prefix, action, entity_id,
    )

    # Clear pending confirmation regardless — button click is definitive
    clear_pending_confirmation(user["id"])

    if prefix == "cancel":
        edit_telegram_message(
            chat_id, message_id,
            "❌ Cancelled. No changes made.",
            remove_keyboard(),
        )
        _log_query(database_path, user, callback_data, "cancel", "cancel",
                   extra={"entity_id": entity_id, "via": "button"})
        return

    if prefix == "exp" and action in ("approve", "reject"):
        tg_action = "approve_expense" if action == "approve" else "reject_expense"
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        require_pin_then_execute(tg_action, {"entity_id": entity_id}, message_id,
                                 user, token, chat_id, database_path)
        return

    if prefix == "tkt" and action == "close":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        require_pin_then_execute("close_ticket", {"entity_id": entity_id}, message_id,
                                 user, token, chat_id, database_path)
        return

    if prefix == "task" and action == "done":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        require_pin_then_execute("mark_task_done", {"task_id": entity_id}, message_id,
                                 user, token, chat_id, database_path)
        return

    # Unknown callback — edit message with an error note
    edit_telegram_message(
        chat_id, message_id,
        f"⚠️ Unknown action: {_e(callback_data)}",
        remove_keyboard(),
    )


# ── Phase C.3 — PIN gate helpers ─────────────────────────────────────────────

def require_pin_then_execute(
    intent: str,
    data: dict,
    message_id: int,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Central PIN gate for every write action.

    If the user has no PIN → execute directly.
    If locked → reject with lock message.
    If PIN set and not locked → store PendingPinEntry, prompt for PIN.
    """
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_state import PendingPinEntry, set_pending_pin_entry

    repo = AdminRepository(database_path)
    status = repo.get_telegram_pin_status(user["id"])

    if not status["has_pin"]:
        # No PIN configured — execute immediately
        _dispatch_write_action(intent, data, message_id, user, token, chat_id, database_path)
        return

    if status["locked"]:
        locked_str = (status["locked_until"] or "")[:16].replace("T", " ")
        _send(token, chat_id, f"🔒 Too many wrong PINs. Account locked until {locked_str} UTC.")
        return

    # PIN set and account not locked — request PIN
    set_pending_pin_entry(user["id"], PendingPinEntry(
        user_id=user["id"],
        intent=intent,
        data=data,
        message_id=message_id,
    ))
    _send(token, chat_id, "🔐 Enter your PIN to confirm this action:")
    _log_query(database_path, user, intent, intent, "pin_requested")


def handle_pin_entry(
    user: dict,
    pin_text: str,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Called by the listener when the user types 4-8 digits and has a PendingPinEntry.

    Verifies PIN, dispatches action on success, or sends error/lock message on failure.
    NEVER logs the PIN in any form.
    """
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_state import (
        get_pending_pin_entry, clear_pending_pin_entry,
    )

    repo = AdminRepository(database_path)
    ppe = get_pending_pin_entry(user["id"])
    if not ppe:
        # Expired or never set — treat as normal message
        _send(token, chat_id, "⏳ Your PIN request expired. Please start the action again.")
        return

    result = repo.verify_telegram_pin(user["id"], pin_text)

    if result.get("ok"):
        clear_pending_pin_entry(user["id"])
        logger.info("PIN verified | user=%s | intent=%s", user.get("email"), ppe.intent)
        _log_query(database_path, user, "pin_entry", ppe.intent, "pin_verified")
        _dispatch_write_action(ppe.intent, ppe.data, ppe.message_id, user, token, chat_id, database_path)
    elif result.get("locked"):
        clear_pending_pin_entry(user["id"])
        locked_str = (result.get("locked_until") or "")[:16].replace("T", " ")
        logger.info("PIN locked | user=%s", user.get("email"))
        _log_query(database_path, user, "pin_entry", ppe.intent, "pin_locked")
        _send(token, chat_id, f"🔒 Too many wrong PINs. Account locked until {locked_str} UTC.")
    else:
        remaining = result.get("attempts_remaining", 0)
        logger.info("PIN failed | user=%s | remaining=%s", user.get("email"), remaining)
        _log_query(database_path, user, "pin_entry", ppe.intent, "pin_failed")
        if remaining > 0:
            _send(token, chat_id, f"❌ Wrong PIN. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")
        else:
            _send(token, chat_id, "❌ Wrong PIN.")


def _dispatch_write_action(
    intent: str,
    data: dict,
    message_id: int,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Execute a write action after PIN verification (or when no PIN is set)."""
    if intent == "create_ticket":
        _do_create_ticket_after_pin(data, user, token, chat_id, database_path)
    elif intent in ("approve_expense", "reject_expense", "close_ticket"):
        entity_id = data.get("entity_id", "")
        _execute_action_and_edit(intent, entity_id, message_id, user, chat_id, database_path)
    elif intent == "create_task":
        _do_create_task_after_pin(data, user, token, chat_id, database_path)
    elif intent == "mark_task_done":
        task_id = data.get("task_id", "")
        _execute_task_done_and_edit(task_id, message_id, user, chat_id, database_path)
    elif intent == "update_ticket_status":
        _execute_update_ticket_and_edit(
            data.get("ticket_id", ""), data.get("status", ""), message_id,
            user, chat_id, database_path,
        )
    elif intent == "assign_ticket":
        _execute_update_ticket_and_edit(
            data.get("ticket_id", ""), data.get("assigned_role", ""), message_id,
            user, chat_id, database_path, is_assign=True,
        )
    else:
        logger.warning("_dispatch_write_action: unknown intent %s", intent)


def _do_create_ticket_after_pin(
    collected: dict,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Execute ticket creation after PIN is verified (or no PIN set)."""
    try:
        from app.repositories.admin_repository import AdminRepository
        from app.services.tool_executor import ToolExecutor
        repo = AdminRepository(database_path)
        executor = ToolExecutor(repo, user)
        result = executor.execute("create_ticket", collected)
        if result.get("error"):
            raise ValueError(result["error"])
        ticket = result.get("ticket", {})
        ticket_id = _e(ticket.get("ticket_id", "?"))
        title = _e(collected.get("title", ""))
        branch = _e(collected.get("branch", ""))
        _send(token, chat_id, (
            f"✅ <b>Ticket created!</b>\n\n"
            f"<b>ID:</b> #{ticket_id}\n"
            f"<b>Title:</b> {title}\n"
            f"<b>Status:</b> Open\n"
            f"<b>Branch:</b> {branch}\n\n"
            "<i>View in the web app for full details.</i>"
        ))
        try:
            from app.services.telegram_service import send_telegram_sync
            send_telegram_sync(
                f"🎫 <b>New Ticket Created</b>\n"
                f"ID: {ticket.get('ticket_id', '—')}\n"
                f"Title: {ticket.get('title', '—')}\n"
                f"Category: {ticket.get('category', '—')}\n"
                f"Priority: {ticket.get('priority', '—')}\n"
                f"By: {user.get('name', user.get('email', '—'))}"
            )
        except Exception as alert_exc:  # noqa: BLE001
            logger.warning("Outbound alert error: %s", alert_exc)
        logger.info("Telegram create_ticket success | user=%s | ticket=%s", user.get("email"), ticket_id)
        _log_query(database_path, user, "confirm", "create_ticket", "success", extra={"ticket_id": ticket_id})
    except Exception as exc:  # noqa: BLE001
        logger.error("_do_create_ticket_after_pin error: %s", exc, exc_info=True)
        _send(token, chat_id, "⚠️ Something went wrong creating the ticket. Please try again or use the web app.")
        _log_query(database_path, user, "confirm", "create_ticket", "error")


def _do_create_task_after_pin(
    collected: dict,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Execute task creation after PIN is verified (or no PIN set)."""
    try:
        from datetime import date, timedelta
        from app.repositories.admin_repository import AdminRepository
        from app.services.tool_executor import ToolExecutor
        repo = AdminRepository(database_path)
        executor = ToolExecutor(repo, user)
        due = collected.get("due_date", "")
        if not due:
            due = (date.today() + timedelta(days=7)).isoformat()
        task_data = {
            "title":         collected.get("title", ""),
            "assigned_role": collected.get("assigned_role", user.get("role", "admin")),
            "due_date":      due,
        }
        result = executor.execute("create_task", task_data)
        if result.get("error"):
            raise ValueError(result["error"])
        task = result.get("task", {})
        task_id = _e(task.get("task_id", "?"))
        title = _e(collected.get("title", ""))
        _send(token, chat_id, (
            f"✅ <b>Task created!</b>\n\n"
            f"<b>ID:</b> {task_id}\n"
            f"<b>Title:</b> {title}\n"
            f"<b>Assigned to:</b> {_e(collected.get('assigned_role', ''))}\n"
            f"<b>Due:</b> {due}\n\n"
            "<i>View in the web app for full details.</i>"
        ))
        logger.info("Telegram create_task success | user=%s | task=%s", user.get("email"), task_id)
        _log_query(database_path, user, "confirm", "create_task", "success", extra={"task_id": task_id})
    except Exception as exc:  # noqa: BLE001
        logger.error("_do_create_task_after_pin error: %s", exc, exc_info=True)
        _send(token, chat_id, "⚠️ Something went wrong creating the task. Please try again or use the web app.")
        _log_query(database_path, user, "confirm", "create_task", "error")


def _execute_task_done_and_edit(
    task_id: str,
    message_id: int,
    user: dict,
    chat_id: int,
    database_path: str,
) -> None:
    """Mark a task as Completed and edit the confirmation message."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_buttons import remove_keyboard
    from app.services.telegram_service import edit_telegram_message

    repo = AdminRepository(database_path)
    # Find task by string ID
    tasks = [t for t in repo.list_tasks()
             if t.get("task_id", "").upper() == task_id.upper()]
    if not tasks:
        new_text = f"❓ Task <code>{_e(task_id)}</code> not found."
    else:
        task = tasks[0]
        try:
            repo.update_task_status(task["id"], "Completed")
            new_text = f"✅ <b>{_e(task_id)} marked as done.</b>"
            logger.info("Telegram mark_task_done success | user=%s | task=%s", user.get("email"), task_id)
            _log_query(database_path, user, "mark_task_done", "mark_task_done", "success",
                       extra={"task_id": task_id})
        except Exception as exc:  # noqa: BLE001
            logger.error("_execute_task_done_and_edit error: %s", exc, exc_info=True)
            new_text = "⚠️ Something went wrong. Please try again or use the web app."

    if message_id:
        edit_result = edit_telegram_message(chat_id, message_id, new_text, remove_keyboard())
        if not edit_result.get("ok"):
            _tg_post_html(os.environ.get("TELEGRAM_BOT_TOKEN", ""), chat_id, new_text)
    else:
        _tg_post_html(os.environ.get("TELEGRAM_BOT_TOKEN", ""), chat_id, new_text)


def _execute_update_ticket_and_edit(
    ticket_id: str,
    value: str,
    message_id: int,
    user: dict,
    chat_id: int,
    database_path: str,
    is_assign: bool = False,
) -> None:
    """Update ticket status (or assigned_role) and edit the confirmation message."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.tool_executor import ToolExecutor
    from app.services.telegram_buttons import remove_keyboard
    from app.services.telegram_service import edit_telegram_message

    repo = AdminRepository(database_path)
    executor = ToolExecutor(repo, user)

    try:
        if is_assign:
            role_map = {"it manager": "it_manager", "admin": "admin", "it_manager": "it_manager"}
            assigned_role = role_map.get(value.lower().strip(), value.strip())
            tickets = [t for t in repo.list_tickets()
                       if t.get("ticket_id", "").upper() == ticket_id.upper()]
            if not tickets:
                new_text = f"❓ Ticket <code>{_e(ticket_id)}</code> not found."
            else:
                repo.update_ticket(tickets[0]["id"], assigned_role=assigned_role)
                new_text = f"✅ <b>{_e(ticket_id)} assigned to {_e(assigned_role)}.</b>"
        else:
            # Normalize status
            status_map = {
                "in progress": "In Progress", "inprogress": "In Progress",
                "open": "Open", "closed": "Closed", "resolved": "Closed",
                "pending": "Pending",
            }
            status = status_map.get(value.lower().strip(), value.strip().title())
            result = executor.execute("ticket_status_update", {"ticket_id": ticket_id, "status": status})
            if result.get("error"):
                raise ValueError(result["error"])
            new_text = f"✅ <b>{_e(ticket_id)} updated to {_e(status)}.</b>"

        logger.info("Telegram update_ticket success | user=%s | ticket=%s", user.get("email"), ticket_id)
        _log_query(database_path, user, "update_ticket", "update_ticket", "success",
                   extra={"ticket_id": ticket_id, "value": value})
    except Exception as exc:  # noqa: BLE001
        logger.error("_execute_update_ticket_and_edit error: %s", exc, exc_info=True)
        new_text = f"⚠️ {_e(str(exc))}" if isinstance(exc, ValueError) else "⚠️ Something went wrong."

    if message_id:
        edit_result = edit_telegram_message(chat_id, message_id, new_text, remove_keyboard())
        if not edit_result.get("ok"):
            _tg_post_html(os.environ.get("TELEGRAM_BOT_TOKEN", ""), chat_id, new_text)
    else:
        _tg_post_html(os.environ.get("TELEGRAM_BOT_TOKEN", ""), chat_id, new_text)


def _send_task_done_confirmation(
    user: dict,
    task_id_str: str,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Fetch task and send a mark-done confirmation message with inline buttons."""
    from app.repositories.admin_repository import AdminRepository
    from app.services.telegram_buttons import task_done_keyboard
    from app.services.telegram_service import send_telegram_with_buttons

    if user.get("role") not in ("admin", "it_manager"):
        _send(token, chat_id, "🔒 You don't have permission to update task status.")
        return

    repo = AdminRepository(database_path)
    tasks = [t for t in repo.list_tasks()
             if t.get("task_id", "").upper() == task_id_str.upper()]
    if not tasks:
        _send(token, chat_id, f"❓ Task <code>{_e(task_id_str)}</code> not found.")
        return
    task = tasks[0]
    title = _e(task.get("title", ""))
    status = _e(task.get("status", ""))
    assigned = _e(task.get("assigned_to", ""))
    due = str(task.get("due_date", ""))[:10]
    tid = _e(task.get("task_id", task_id_str))

    text = (
        f"<b>Mark this task as done?</b>\n\n"
        f"<b>ID:</b> {tid}\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Assigned to:</b> {assigned}\n"
        f"<b>Due:</b> {due}"
    )
    keyboard = task_done_keyboard(tid)
    result = send_telegram_with_buttons(chat_id, text, keyboard)
    if result.get("ok"):
        from app.services.telegram_state import PendingConfirmation, set_pending_confirmation
        set_pending_confirmation(user["id"], PendingConfirmation(
            user_id=user["id"],
            action="mark_task_done",
            entity_id=tid,
            message_id=result.get("message_id", 0),
        ))
    else:
        logger.warning("Failed to send task done confirmation: %s", result.get("error"))


# ── Phase C.1 — create_ticket slot-filling helpers ───────────────────────────

def _next_missing_slot(collected: dict[str, str], slots: tuple[str, ...] = _TICKET_SLOTS) -> str | None:
    """Return the name of the first unfilled slot, or None if all filled."""
    for slot in slots:
        if not collected.get(slot, "").strip():
            return slot
    return None


def _slot_prompt(slot: str, prompts: dict[str, str] = _TICKET_SLOT_PROMPTS) -> str:
    """Return the prompt for the given slot, with cancel hint."""
    prompt = prompts.get(slot, f"What is the {slot}?")
    return f"{prompt}\n\n<i>(Send /cancel to stop.)</i>"


def _confirmation_text(collected: dict[str, str]) -> str:
    return (
        "<b>Please confirm this ticket:</b>\n\n"
        f"<b>Title:</b> {_e(collected.get('title', ''))}\n"
        f"<b>Category:</b> {_e(collected.get('category', ''))}\n"
        f"<b>Priority:</b> {_e(collected.get('priority', ''))}\n"
        f"<b>Branch:</b> {_e(collected.get('branch', ''))}\n\n"
        "Reply <b>yes</b> to create or <b>no</b> to cancel."
    )


def _task_confirmation_text(collected: dict[str, str]) -> str:
    from datetime import date, timedelta
    due = collected.get("due_date", "") or (date.today() + timedelta(days=7)).isoformat()
    return (
        "<b>Please confirm this task:</b>\n\n"
        f"<b>Title:</b> {_e(collected.get('title', ''))}\n"
        f"<b>Assigned to:</b> {_e(collected.get('assigned_role', ''))}\n"
        f"<b>Due:</b> {_e(due)}\n\n"
        "Reply <b>yes</b> to create or <b>no</b> to cancel."
    )


def _handle_slot_filling(
    session: "TelegramSession",
    text: str,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Process one message in an active slot-filling session."""
    from app.services.telegram_state import clear_session, update_activity, set_session
    user_id = user["id"]
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # ── /cancel always works mid-session ─────────────────────────────────────
    if text_lower.startswith("/cancel"):
        clear_session(user_id)
        _send(token, chat_id, "❌ Cancelled. Nothing was created.")
        _log_query(database_path, user, text, "create_ticket", "cancel")
        return

    # ── Confirmation phase ────────────────────────────────────────────────────
    if session.awaiting_confirmation:
        if text_lower in _CONFIRM_WORDS:
            # Clear slot session — data is now passed to PIN gate / executor
            collected = dict(session.collected)
            intent = session.intent
            clear_session(user_id)
            require_pin_then_execute(
                intent, collected, 0,
                user, token, chat_id, database_path,
            )
            _log_query(database_path, user, text, intent, "confirmed")

        elif text_lower in _CANCEL_WORDS:
            clear_session(user_id)
            _send(token, chat_id, "❌ Cancelled. Nothing was created.")
            _log_query(database_path, user, text, "create_ticket", "cancel")

        else:
            # Unrecognised — re-send confirmation prompt
            update_activity(user_id)
            _send(token, chat_id,
                _confirmation_text(session.collected) +
                "\n\n<i>Please reply <b>yes</b> or <b>no</b>.</i>"
            )
        return

    # ── Slot collection phase ─────────────────────────────────────────────────
    if not text_clean:
        next_slot = _next_missing_slot(session.collected)
        slot_label = next_slot or "value"
        _send(token, chat_id,
            f"Please send the <b>{_e(slot_label)}</b>, or /cancel to stop.")
        return

    next_slot = _next_missing_slot(session.collected)
    if next_slot is None:
        # Shouldn't happen, but guard anyway
        update_activity(user_id)
        session.awaiting_confirmation = True
        set_session(user_id, session)
        _send(token, chat_id, _confirmation_text(session.collected))
        return

    # Collect the slot value
    session.collected[next_slot] = text_clean
    update_activity(user_id)

    logger.info(
        "Telegram slot collected | user=%s | slot=%s | value=%r",
        user.get("email"), next_slot, text_clean[:50],
    )

    # Check if all slots are now filled
    next_missing = _next_missing_slot(session.collected)
    if next_missing is None:
        # All slots filled — show confirmation
        session.awaiting_confirmation = True
        set_session(user_id, session)
        _send(token, chat_id, _confirmation_text(session.collected))
    else:
        set_session(user_id, session)
        _send(token, chat_id, _slot_prompt(next_missing))


# ── Phase C.3 — create_task slot-filling ──────────────────────────────────────

def _handle_task_slot_filling(
    session: "TelegramSession",
    text: str,
    user: dict,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Process one message in an active create_task slot-filling session."""
    from app.services.telegram_state import clear_session, update_activity, set_session
    user_id = user["id"]
    text_clean = text.strip()
    text_lower = text_clean.lower()

    if text_lower.startswith("/cancel"):
        clear_session(user_id)
        _send(token, chat_id, "❌ Cancelled. Nothing was created.")
        _log_query(database_path, user, text, "create_task", "cancel")
        return

    if session.awaiting_confirmation:
        if text_lower in _CONFIRM_WORDS:
            collected = dict(session.collected)
            clear_session(user_id)
            require_pin_then_execute("create_task", collected, 0, user, token, chat_id, database_path)
            _log_query(database_path, user, text, "create_task", "confirmed")
        elif text_lower in _CANCEL_WORDS:
            clear_session(user_id)
            _send(token, chat_id, "❌ Cancelled. Nothing was created.")
            _log_query(database_path, user, text, "create_task", "cancel")
        else:
            update_activity(user_id)
            _send(token, chat_id,
                _task_confirmation_text(session.collected) +
                "\n\n<i>Please reply <b>yes</b> or <b>no</b>.</i>"
            )
        return

    # /skip for due_date slot
    if text_lower == "/skip":
        text_clean = ""  # store empty → will default to 7 days in executor

    next_slot = _next_missing_slot(session.collected, _TASK_SLOTS)
    if next_slot is None:
        session.awaiting_confirmation = True
        set_session(user_id, session)
        _send(token, chat_id, _task_confirmation_text(session.collected))
        return

    # Normalize role input
    if next_slot == "assigned_role":
        role_map = {
            "admin": "admin", "it_manager": "it_manager",
            "it manager": "it_manager", "it": "it_manager",
        }
        normalized = role_map.get(text_lower.strip(), "")
        if not normalized:
            update_activity(user_id)
            _send(token, chat_id, "⚠️ Please send <b>admin</b> or <b>it_manager</b>.")
            return
        text_clean = normalized

    session.collected[next_slot] = text_clean
    update_activity(user_id)

    next_missing = _next_missing_slot(session.collected, _TASK_SLOTS)
    if next_missing is None:
        session.awaiting_confirmation = True
        set_session(user_id, session)
        _send(token, chat_id, _task_confirmation_text(session.collected))
    else:
        set_session(user_id, session)
        _send(token, chat_id, _slot_prompt(next_missing, _TASK_SLOT_PROMPTS))


# ── Main router entry point ───────────────────────────────────────────────────

def handle_telegram_message(
    user: dict,
    text: str,
    token: str,
    chat_id: int,
    database_path: str,
) -> None:
    """Route a registered user's Telegram message through the Conci AI pipeline.

    Never raises — all errors are caught and a friendly message is sent.
    """
    text = text.strip()
    if not text:
        _send(token, chat_id, "Please send a question or command. Try /help for ideas.")
        return

    user_name = _e(user.get("name", "User"))
    role = user.get("role", "")
    text_lower = text.lower()
    user_id = user["id"]

    # ── Phase C.1: active slot-filling session intercepts ALL non-command text ─
    # Commands (/start /register /whoami /help /summary /cancel) are handled
    # by the listener BEFORE reaching this function, so we only see plain text.
    from app.services.telegram_state import (
        get_session, TelegramSession, set_session,
        get_pending_confirmation, clear_pending_confirmation,
    )
    active_session = get_session(user_id)
    if active_session is not None:
        if active_session.intent == "create_task":
            _handle_task_slot_filling(active_session, text, user, token, chat_id, database_path)
        else:
            _handle_slot_filling(active_session, text, user, token, chat_id, database_path)
        return

    # ── Phase C.2: pending confirmation handles typed yes/no fallback ─────────
    # Only reaches here if there is NO active slot-filling session.
    pending = get_pending_confirmation(user_id)
    if pending is not None:
        if text_lower in _CONFIRM_WORDS:
            clear_pending_confirmation(user_id)
            require_pin_then_execute(
                pending.action, {"entity_id": pending.entity_id},
                pending.message_id, user, token, chat_id, database_path,
            )
            return
        elif text_lower in _CANCEL_WORDS or text_lower.startswith("/cancel"):
            clear_pending_confirmation(user_id)
            from app.services.telegram_buttons import remove_keyboard
            from app.services.telegram_service import edit_telegram_message
            edit_telegram_message(
                chat_id, pending.message_id,
                "❌ Cancelled. No changes made.",
                remove_keyboard(),
            )
            return
        # Any other text — user may be trying a new command; fall through
        # and let the normal routing handle it (pending confirmation remains active)

    # ── Phase C.2: text-based approve / reject / close triggers ─────────────
    m_approve = _RE_APPROVE.search(text)
    m_reject  = _RE_REJECT.search(text)
    m_close   = _RE_CLOSE.search(text)

    if m_approve and not m_reject:
        _send_expense_confirmation(user, m_approve.group(1), token, chat_id, database_path)
        _log_query(database_path, user, text, "approve_expense", "confirmation_sent")
        return

    if m_reject:
        expense_id_str = m_reject.group(1)
        if user.get("role") not in ("admin", "finance_manager"):
            _send(token, chat_id, "🔒 You don't have permission to reject expenses.")
            return
        from app.repositories.admin_repository import AdminRepository
        from app.services.telegram_buttons import expense_approval_keyboard
        from app.services.telegram_service import send_telegram_with_buttons
        from app.services.telegram_state import PendingConfirmation, set_pending_confirmation
        repo = AdminRepository(database_path)
        expense = repo.get_expense_by_expense_id(expense_id_str)
        if not expense:
            _send(token, chat_id, f"❓ Expense <code>{_e(expense_id_str)}</code> not found.")
            return
        amount = f"Rs.{float(expense.get('amount', 0)):,.0f}"
        text_msg = (
            f"<b>Approve or reject this expense?</b>\n\n"
            f"<b>ID:</b> {_e(expense_id_str)}\n"
            f"<b>Amount:</b> {amount}\n"
            f"<b>Category:</b> {_e(expense.get('category', ''))}\n"
            f"<b>Submitted by:</b> {_e(expense.get('employee_name', ''))}\n"
            f"<b>Status:</b> {_e(expense.get('status', ''))}"
        )
        keyboard = expense_approval_keyboard(expense_id_str)
        result = send_telegram_with_buttons(chat_id, text_msg, keyboard)
        if result.get("ok"):
            set_pending_confirmation(user["id"], PendingConfirmation(
                user_id=user["id"],
                action="reject_expense",
                entity_id=expense_id_str,
                message_id=result.get("message_id", 0),
            ))
        _log_query(database_path, user, text, "reject_expense", "confirmation_sent")
        return

    if m_close:
        _send_ticket_close_confirmation(user, m_close.group(1), token, chat_id, database_path)
        _log_query(database_path, user, text, "close_ticket", "confirmation_sent")
        return

    # ── Phase C.3: mark_task_done text trigger ───────────────────────────────
    m_done = _RE_MARK_DONE.search(text)
    if m_done:
        _send_task_done_confirmation(user, m_done.group(1), token, chat_id, database_path)
        _log_query(database_path, user, text, "mark_task_done", "confirmation_sent")
        return

    # ── Phase C.3: update_ticket status text trigger ─────────────────────────
    m_upd = _RE_UPDATE_TICKET_STATUS.search(text)
    if m_upd:
        if user.get("role") not in ("admin", "it_manager"):
            _send(token, chat_id, "🔒 You don't have permission to update ticket status.")
            return
        ticket_id_str = m_upd.group(1)
        new_status = m_upd.group(2).strip()
        require_pin_then_execute(
            "update_ticket_status",
            {"ticket_id": ticket_id_str, "status": new_status},
            0, user, token, chat_id, database_path,
        )
        _log_query(database_path, user, text, "update_ticket_status", "pin_requested")
        return

    # ── Phase C.3: assign_ticket text trigger ────────────────────────────────
    m_assign = _RE_ASSIGN_TICKET.search(text)
    if m_assign:
        if user.get("role") not in ("admin", "it_manager"):
            _send(token, chat_id, "🔒 You don't have permission to assign tickets.")
            return
        ticket_id_str = m_assign.group(1)
        assigned_role = m_assign.group(2)
        require_pin_then_execute(
            "assign_ticket",
            {"ticket_id": ticket_id_str, "assigned_role": assigned_role},
            0, user, token, chat_id, database_path,
        )
        _log_query(database_path, user, text, "assign_ticket", "pin_requested")
        return

    # ── Daily summary shortcut (also triggered by /summary in the listener) ──
    if any(phrase in text_lower for phrase in _SUMMARY_PHRASES):
        try:
            reply = _fmt_daily_summary(user, database_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("telegram_router daily_summary error: %s", exc, exc_info=True)
            reply = "⚠️ Something went wrong loading the summary. Try again."
        _send(token, chat_id, reply)
        _log_query(database_path, user, text, "daily_summary", "success")
        return

    # ── Help shortcut ─────────────────────────────────────────────────────────
    if text_lower in ("help", "?"):
        _send(token, chat_id, _fmt_help(user))
        return

    # ── Intent classification ─────────────────────────────────────────────────
    try:
        from app.services.conci_agent import ConciAgentIntentService
        intent_result = ConciAgentIntentService.classify(text)
        intent = intent_result.intent
        entities = dict(intent_result.entities or {})
    except Exception as exc:  # noqa: BLE001
        logger.error("telegram_router classify error: %s", exc, exc_info=True)
        _send(token, chat_id, "⚠️ Something went wrong. Please try again.")
        return

    logger.info(
        "Telegram query | user=%s | role=%s | text=%r | intent=%s | confidence=%.2f",
        user.get("email"), role, text[:80], intent, float(intent_result.confidence or 0),
    )

    # ── Phase C.1: create_ticket — start guided slot-filling ─────────────────
    if intent == "create_ticket":
        new_session = TelegramSession(user_id=user_id, intent="create_ticket")
        set_session(user_id, new_session)
        _send(token, chat_id, (
            f"🎫 <b>Let's create a ticket, {user_name}.</b>\n\n"
            + _slot_prompt("title")
        ))
        logger.info("Telegram create_ticket session started | user=%s", user.get("email"))
        _log_query(database_path, user, text, "create_ticket", "session_start")
        return

    # ── Phase C.3: create_task — start guided slot-filling ───────────────────
    if intent == "create_task" or any(p in text_lower for p in _CREATE_TASK_PHRASES):
        if user.get("role") not in ("admin", "it_manager"):
            _send(token, chat_id, "🔒 Only Admin or IT Manager can create tasks.")
            _log_query(database_path, user, text, "create_task", "refused_permission")
            return
        new_session = TelegramSession(user_id=user_id, intent="create_task")
        set_session(user_id, new_session)
        _send(token, chat_id, (
            f"📋 <b>Let's create a task, {user_name}.</b>\n\n"
            + _slot_prompt("title", _TASK_SLOT_PROMPTS)
        ))
        logger.info("Telegram create_task session started | user=%s", user.get("email"))
        _log_query(database_path, user, text, "create_task", "session_start")
        return

    # ── Write intent → Phase C refusal (other write intents pending C.2/C.3) ─
    if intent in _WRITE_INTENTS:
        _send(token, chat_id, (
            "⚠️ I can't make that change from Telegram yet — coming soon.\n\n"
            "Use the <b>Conci AI sidebar</b> in the web app for now."
        ))
        _log_query(database_path, user, text, intent, "refused_write")
        return

    # ── Utility intents ───────────────────────────────────────────────────────
    if intent == "help" or intent == "unsupported":
        if intent == "unsupported":
            _send(token, chat_id,
                f"🤔 I didn't understand that.\n\n{_HELP_TEXT}")
        else:
            _send(token, chat_id, _fmt_help(user))
        _log_query(database_path, user, text, intent, "success")
        return

    if intent == "casual_identity":
        _send(token, chat_id, (
            f"👋 I'm <b>Agent Concierge</b> — your AI assistant for IT operations.\n\n"
            f"You're logged in as <b>{user_name}</b>. Try /help to see what I can do."
        ))
        _log_query(database_path, user, text, intent, "success")
        return

    if intent == "utility_date":
        from datetime import date
        today_str = date.today().strftime("%d %B %Y")
        _send(token, chat_id, f"📅 Today is <b>{today_str}</b>.")
        return

    if intent == "utility_time":
        time_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
        _send(token, chat_id, f"🕐 Current time: <b>{time_str}</b>.")
        return

    # ── Data fetch via ToolExecutor ───────────────────────────────────────────
    if intent not in _READ_INTENTS:
        _send(token, chat_id,
            f"🤔 I don't support <i>{_e(intent)}</i> yet.\n\n{_HELP_TEXT}")
        _log_query(database_path, user, text, intent, "unsupported")
        return

    try:
        from app.repositories.admin_repository import AdminRepository
        from app.services.tool_executor import ToolExecutor

        repo = AdminRepository(database_path)
        executor = ToolExecutor(repo, user)
        data = executor.execute(intent, entities)

        if data.get("error"):
            err_msg = str(data["error"])
            # Role-based permission errors should be surfaced clearly
            if "permission" in err_msg.lower() or "denied" in err_msg.lower():
                reply = f"🔒 {_e(err_msg)}"
            else:
                logger.warning("telegram_router executor error: %s (intent=%s)", err_msg, intent)
                reply = f"⚠️ {_e(err_msg)}"
        else:
            reply = _format_result(intent, data)

    except Exception as exc:  # noqa: BLE001
        logger.error("telegram_router fetch error: %s", exc, exc_info=True)
        reply = "⚠️ Something went wrong fetching data. Try again."
        _log_query(database_path, user, text, intent, "error")
        _send(token, chat_id, reply)
        return

    _send(token, chat_id, reply)
    _log_query(database_path, user, text, intent, "success")


def _format_result(intent: str, data: dict) -> str:
    """Dispatch data to the right formatter."""
    if intent in ("open_tickets", "my_tickets", "recent_tickets", "ticket_status"):
        return _fmt_tickets(data, intent)

    if intent in ("open_tasks", "my_tasks", "overdue_tasks"):
        return _fmt_tasks(data, intent)

    if intent in (
        "pending_approvals", "pending_expenses", "expense_summary",
        "expenses_by_month", "expenses_by_category",
        "expenses_last_month", "expenses_this_month",
    ):
        return _fmt_expenses(data, intent)

    if intent in ("active_vendors", "vendor_list", "vendor_billing", "vendor_count", "vendor_details"):
        return _fmt_vendors(data, intent)

    if intent in ("inventory_summary", "inventory_in_use", "inventory_submitted_vendor", "inventory_recent_updates"):
        return _fmt_inventory(data, intent)

    if intent in ("travel_spend", "travel_recent_records"):
        # Reuse a generic items formatter
        records = data.get("records") or data.get("items") or []
        if not records:
            return "✨ No travel records found."
        shown, cut = _truncate(records)
        lines = [f"<b>✈️ Travel Records ({len(records)})</b>\n"]
        for r in shown:
            dest = _e(r.get("destination_to") or r.get("destination_from") or "—")
            spend = f"₹{float(r.get('actual_spend') or r.get('estimated_budget') or 0):,.0f}"
            date_str = str(r.get("travel_start_date") or "")[:10]
            lines.append(f"• {dest} — {spend}" + (f" — {date_str}" if date_str else ""))
        if cut:
            lines.append(f"\n<i>...and {cut} more.</i>")
        return "\n".join(lines)

    # Fallback — shouldn't normally reach here
    return "✅ Got it — data fetched. Open the web app for full details."


def _log_query(
    database_path: str,
    user: dict,
    text: str,
    intent: str,
    status: str,
    extra: dict | None = None,
) -> None:
    """Write a row to agent_logs for every Telegram query. Silently swallowed on error."""
    _INFO_STATUSES = {"success", "refused_write", "cancel", "session_start"}
    try:
        from app.repositories.admin_repository import AdminRepository
        repo = AdminRepository(database_path)
        data: dict = {
            "event": "telegram_query",
            "user_id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("role"),
            "intent": intent,
            "query_status": status,
            "text_snippet": text[:80],
        }
        if extra:
            data.update(extra)
        repo.create_agent_log(
            agent_name="telegram_router",
            status="info" if status in _INFO_STATUSES else "error",
            message=f"Telegram query from {user.get('email','')} | intent={intent} | {status}",
            data=data,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("telegram_router log_query failed: %s", exc)
