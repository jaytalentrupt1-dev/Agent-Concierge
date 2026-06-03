from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.services.telegram_service import send_telegram_sync

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    logger.warning("apscheduler not installed — background agents disabled. Run: pip install apscheduler")

_scheduler: "BackgroundScheduler | None" = None


def _make_repo(database_path: str):
    from app.repositories.admin_repository import AdminRepository
    return AdminRepository(database_path)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────
# AGENT 1: ticket_watchdog — runs every 1 hour
# ─────────────────────────────────────────────────────────
def ticket_watchdog(database_path: str) -> None:
    try:
        repo = _make_repo(database_path)
        now = datetime.now(timezone.utc)
        tickets = repo.list_tickets()
        open_tickets = [t for t in tickets if t.get("status", "").lower() == "open"]
        overdue_count = 0
        auto_assigned = 0

        for ticket in open_tickets:
            created_at = _parse_dt(ticket.get("created_at"))
            if created_at and (now - created_at) > timedelta(hours=48):
                repo.update_ticket(ticket["id"], status="Overdue")
                repo.add_notification({
                    "title":               f"Ticket Overdue: {ticket.get('ticket_id', '')}",
                    "message":             f"{ticket.get('title', '')} has been open for more than 48 hours.",
                    "type":                "warning",
                    "related_entity_type": "ticket",
                    "related_entity_id":   ticket.get("ticket_id", str(ticket["id"])),
                    "target_role":         "admin",
                })
                overdue_count += 1

            if not ticket.get("assigned_role") or ticket.get("assigned_role") == "admin":
                auto_role = "it_manager" if ticket.get("ticket_type", "").lower() == "it" else "admin"
                repo.update_ticket(ticket["id"], assigned_role=auto_role)
                repo.add_notification({
                    "title":               f"New Ticket Assigned: {ticket.get('ticket_id', '')}",
                    "message":             f"{ticket.get('title', '')} auto-assigned to {auto_role.replace('_', ' ').title()}.",
                    "type":                "info",
                    "related_entity_type": "ticket",
                    "related_entity_id":   ticket.get("ticket_id", str(ticket["id"])),
                    "target_role":         auto_role,
                })
                auto_assigned += 1

        summary = (
            f"ticket_watchdog: checked {len(open_tickets)} tickets, "
            f"marked {overdue_count} overdue, auto-assigned {auto_assigned}"
        )
        logger.info(summary)
        repo.create_agent_log(
            agent_name="ticket_watchdog",
            status="success",
            message=summary,
            data={"open_tickets": len(open_tickets), "overdue": overdue_count, "auto_assigned": auto_assigned},
        )
        tg = send_telegram_sync(f"🎫 <b>Ticket Watchdog</b>\n{summary}")
        if not tg.get("ok"):
            logger.warning("ticket_watchdog Telegram send failed: %s", tg.get("error"))
    except Exception as exc:
        logger.error("ticket_watchdog error: %s", exc)
        try:
            _make_repo(database_path).create_agent_log(
                agent_name="ticket_watchdog",
                status="error",
                message=str(exc),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# AGENT 2: expense_monitor — runs every 2 hours
# ─────────────────────────────────────────────────────────
def expense_monitor(database_path: str) -> None:
    try:
        repo = _make_repo(database_path)
        now = datetime.now(timezone.utc)
        all_expenses = repo.list_expenses()
        pending = [
            ex for ex in all_expenses
            if ex.get("status", "").lower() in ("pending approval", "pending_approval")
        ]
        alerted = 0

        for expense in pending:
            created_at = _parse_dt(expense.get("created_at"))
            amount = float(expense.get("amount", 0))
            exp_id = expense.get("expense_id", str(expense["id"]))

            if created_at and (now - created_at) > timedelta(hours=72):
                age_days = (now - created_at).days
                repo.add_notification({
                    "title":               "Expense Awaiting Approval",
                    "message":             f"{exp_id} — ₹{amount:,.0f} has been pending for {age_days} day(s).",
                    "type":                "warning",
                    "related_entity_type": "expense",
                    "related_entity_id":   exp_id,
                    "target_role":         "finance_manager",
                })
                alerted += 1

            if amount > 100000:
                repo.add_notification({
                    "title":               "High Value Expense",
                    "message":             f"{exp_id} — ₹{amount:,.0f} requires Admin review.",
                    "type":                "alert",
                    "related_entity_type": "expense",
                    "related_entity_id":   exp_id,
                    "target_role":         "admin",
                })

        summary = f"expense_monitor: checked {len(pending)} pending expenses, sent {alerted} alerts"
        logger.info(summary)
        repo.create_agent_log(
            agent_name="expense_monitor",
            status="success",
            message=summary,
            data={"pending_expenses": len(pending), "alerts_sent": alerted},
        )
        tg = send_telegram_sync(f"💰 <b>Expense Monitor</b>\n{summary}")
        if not tg.get("ok"):
            logger.warning("expense_monitor Telegram send failed: %s", tg.get("error"))
    except Exception as exc:
        logger.error("expense_monitor error: %s", exc)
        try:
            _make_repo(database_path).create_agent_log(
                agent_name="expense_monitor",
                status="error",
                message=str(exc),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# AGENT 3: inventory_monitor — runs every 6 hours
# ─────────────────────────────────────────────────────────
def inventory_monitor(database_path: str) -> None:
    try:
        repo = _make_repo(database_path)
        now = datetime.now(timezone.utc)
        items = repo.list_inventory_items()
        submitted = [
            i for i in items
            if i.get("status", "").lower() in ("submitted to vendor", "submitted_to_vendor")
        ]
        alerted = 0

        for item in submitted:
            updated_at = _parse_dt(item.get("updated_at"))
            if updated_at and (now - updated_at) > timedelta(days=30):
                age_days = (now - updated_at).days
                repo.add_notification({
                    "title":               "Asset Pending with Vendor",
                    "message":             (
                        f"{item.get('serial_number', item.get('serial_no', ''))} — "
                        f"{item.get('model', item.get('model_no', ''))} "
                        f"submitted {age_days} day(s) ago."
                    ),
                    "type":                "warning",
                    "related_entity_type": "inventory",
                    "related_entity_id":   item.get("item_id", str(item["id"])),
                    "target_role":         "it_manager",
                })
                alerted += 1

        summary = f"inventory_monitor: checked {len(submitted)} submitted items, sent {alerted} alerts"
        logger.info(summary)
        repo.create_agent_log(
            agent_name="inventory_monitor",
            status="success",
            message=summary,
            data={"submitted_items": len(submitted), "alerts_sent": alerted},
        )
        tg = send_telegram_sync(f"📦 <b>Inventory Monitor</b>\n{summary}")
        if not tg.get("ok"):
            logger.warning("inventory_monitor Telegram send failed: %s", tg.get("error"))
    except Exception as exc:
        logger.error("inventory_monitor error: %s", exc)
        try:
            _make_repo(database_path).create_agent_log(
                agent_name="inventory_monitor",
                status="error",
                message=str(exc),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# AGENT 4: daily_briefing — runs every day at 8 AM UTC
# ─────────────────────────────────────────────────────────
def daily_briefing(database_path: str) -> None:
    try:
        repo = _make_repo(database_path)
        today = datetime.now(timezone.utc).date().isoformat()
        tickets = repo.list_tickets()
        tasks = repo.list_tasks()
        expenses = repo.list_expenses()
        vendors = repo.list_vendors()

        open_tickets = len([t for t in tickets if t.get("status", "").lower() == "open"])
        overdue_tasks = len([
            t for t in tasks
            if t.get("status", "").lower() not in ("completed", "cancelled", "closed")
            and t.get("due_date") and str(t.get("due_date", "")) < today
        ])
        pending_expenses = len([
            ex for ex in expenses
            if ex.get("status", "").lower() in ("pending approval", "pending_approval")
        ])
        active_vendors = len([v for v in vendors if v.get("status", "").lower() == "active"])

        summary_text = (
            f"Open Tickets: {open_tickets} | "
            f"Overdue Tasks: {overdue_tasks} | "
            f"Pending Expenses: {pending_expenses} | "
            f"Active Vendors: {active_vendors}"
        )

        # Admin gets the full daily briefing
        repo.add_notification({
            "title":               "Daily Briefing",
            "message":             summary_text,
            "type":                "info",
            "related_entity_type": "system",
            "related_entity_id":   "daily_briefing",
            "target_role":         "admin",
        })

        # IT Manager gets ticket + task summary
        if open_tickets > 0 or overdue_tasks > 0:
            repo.add_notification({
                "title":               "Daily IT Summary",
                "message":             f"Open Tickets: {open_tickets} | Overdue Tasks: {overdue_tasks}",
                "type":                "info",
                "related_entity_type": "system",
                "related_entity_id":   "daily_briefing",
                "target_role":         "it_manager",
            })

        # Finance Manager gets expense summary
        if pending_expenses > 0:
            repo.add_notification({
                "title":               "Daily Finance Summary",
                "message":             f"Pending Expenses awaiting approval: {pending_expenses}",
                "type":                "info",
                "related_entity_type": "system",
                "related_entity_id":   "daily_briefing",
                "target_role":         "finance_manager",
            })

        logger.info("daily_briefing: sent — %s", summary_text)
        repo.create_agent_log(
            agent_name="daily_briefing",
            status="success",
            message=f"Daily briefing sent: {summary_text}",
            data={
                "open_tickets": open_tickets,
                "overdue_tasks": overdue_tasks,
                "pending_expenses": pending_expenses,
                "active_vendors": active_vendors,
            },
        )
        tg = send_telegram_sync(f"📋 <b>Daily Briefing</b>\n{summary_text}")
        if not tg.get("ok"):
            logger.warning("daily_briefing Telegram send failed: %s", tg.get("error"))
    except Exception as exc:
        logger.error("daily_briefing error: %s", exc)
        try:
            _make_repo(database_path).create_agent_log(
                agent_name="daily_briefing",
                status="error",
                message=str(exc),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# Scheduler lifecycle
# ─────────────────────────────────────────────────────────
def start_scheduler(database_path: str) -> None:
    global _scheduler
    if not _APSCHEDULER_AVAILABLE:
        return
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        ticket_watchdog,
        "interval",
        hours=1,
        id="ticket_watchdog",
        kwargs={"database_path": database_path},
        replace_existing=True,
    )
    _scheduler.add_job(
        expense_monitor,
        "interval",
        hours=2,
        id="expense_monitor",
        kwargs={"database_path": database_path},
        replace_existing=True,
    )
    _scheduler.add_job(
        inventory_monitor,
        "interval",
        hours=6,
        id="inventory_monitor",
        kwargs={"database_path": database_path},
        replace_existing=True,
    )
    _scheduler.add_job(
        daily_briefing,
        "cron",
        hour=8,
        minute=0,
        id="daily_briefing",
        kwargs={"database_path": database_path},
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: ticket_watchdog (1h), expense_monitor (2h), "
        "inventory_monitor (6h), daily_briefing (8AM UTC)"
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
