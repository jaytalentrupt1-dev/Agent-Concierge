"""Two-way Telegram listener — Phase A + B.

Polls Telegram's getUpdates API (long-polling) in a daemon thread.
Handles:
  /start      — welcome + registration instructions
  /register   — link Telegram chat to a web-app account via 6-digit code
  /unregister — remove the link
  /whoami     — show linked account info
  /summary    — daily summary (Phase B)
  /help       — list available commands (Phase B)
  <any other> — routes through Conci AI intent pipeline (Phase B) for registered users,
                registration instructions for unregistered users

Environment variables required (add to .env, do NOT auto-edit):
  TELEGRAM_BOT_TOKEN       — existing variable (reused)
  TELEGRAM_BOT_USERNAME    — bot @username without the @ (e.g. MyAgentBot)
  TELEGRAM_LISTENER_ENABLED — set to "true" to activate

Uses only stdlib — no new pip dependencies.
Never raises an exception that could crash the FastAPI process.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# ── Module-level state ───────────────────────────────────────────────────────

_stop_event: threading.Event | None = None
_listener_thread: threading.Thread | None = None

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# ── Low-level Telegram helpers ────────────────────────────────────────────────

def _tg_get(token: str, method: str, **params: Any) -> dict:
    """GET request to Telegram Bot API. Returns {} on any error."""
    filtered = {k: str(v) for k, v in params.items() if v is not None}
    url = _TELEGRAM_API.format(token=token, method=method)
    if filtered:
        url = f"{url}?{urllib.parse.urlencode(filtered)}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Telegram GET %s failed: %s", method, exc)
        return {"ok": False, "error": str(exc)}


def _tg_post(token: str, method: str, **payload: Any) -> dict:
    """POST request to Telegram Bot API. Returns {} on any error."""
    url = _TELEGRAM_API.format(token=token, method=method)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Telegram POST %s failed: %s", method, exc)
        return {"ok": False, "error": str(exc)}


def _reply(token: str, chat_id: int, text: str) -> None:
    """Send a message to a chat, logging failures but never raising."""
    result = _tg_post(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
    if not result.get("ok"):
        logger.warning("Telegram reply to %s failed: %s", chat_id, result.get("error"))


# ── Message handler ───────────────────────────────────────────────────────────

def _handle_update(update: dict, token: str, database_path: str) -> None:
    """Process a single Telegram update. All exceptions are caught internally."""
    try:
        # ── callback_query — inline button click (Phase C.2) ─────────────────
        callback_query = update.get("callback_query")
        if callback_query:
            cbq_id: str = callback_query.get("id", "")
            from_user: dict = callback_query.get("from", {})
            cbq_chat_id: int = callback_query.get("message", {}).get("chat", {}).get("id", 0)
            message_id: int = callback_query.get("message", {}).get("message_id", 0)
            callback_data: str = callback_query.get("data", "")

            # Always acknowledge the button click first (removes spinner)
            from app.services.telegram_service import answer_callback_query
            answer_callback_query(cbq_id)

            from app.repositories.admin_repository import AdminRepository
            repo = AdminRepository(database_path)
            cbq_user = repo.get_user_by_telegram_chat_id(cbq_chat_id)

            if not cbq_user:
                _reply(token, cbq_chat_id, "❓ Not registered. Send /start to link your account.")
                return

            from app.services.telegram_router import handle_callback
            handle_callback(cbq_user, callback_data, message_id, cbq_chat_id, database_path)
            return

        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat_id: int = message["chat"]["id"]
        from_user: dict = message.get("from", {})
        text: str = (message.get("text") or "").strip()
        sender_name = from_user.get("first_name", "") or from_user.get("username", "User")

        logger.info("Telegram incoming | chat_id=%s | from=%s | text=%r", chat_id, sender_name, text[:80])

        # Lazy-import to avoid circular deps + support hot-reload
        from app.repositories.admin_repository import AdminRepository
        repo = AdminRepository(database_path)

        # ── /start ────────────────────────────────────────────────────────────
        if text.lower().startswith("/start"):
            _reply(token, chat_id, (
                "👋 <b>Welcome to Agent Concierge!</b>\n\n"
                "To link this Telegram account to your web-app account:\n\n"
                "1. Log into the web app\n"
                "2. Go to <b>Settings → Telegram Integration</b>\n"
                "3. Click <b>Connect Telegram</b> — you'll get a 6-digit code\n"
                "4. Send me: <code>/register &lt;code&gt;</code>\n\n"
                "Once linked, you can query Agent Concierge directly from here."
            ))
            return

        # ── /register <code> ──────────────────────────────────────────────────
        if text.lower().startswith("/register"):
            parts = text.split()
            if len(parts) < 2:
                _reply(token, chat_id, (
                    "⚠️ Please include your code: <code>/register 123456</code>\n\n"
                    "Get a code from <b>Settings → Telegram Integration</b> in the web app."
                ))
                return

            code = parts[1].strip()
            reg = repo.get_telegram_registration_code(code)

            if not reg:
                _reply(token, chat_id, (
                    "❌ Invalid or expired code.\n\n"
                    "Generate a new one from <b>Settings → Telegram Integration</b> in the web app."
                ))
                return

            if reg.get("used"):
                _reply(token, chat_id, "❌ This code has already been used. Please generate a new one.")
                return

            # Mark used and link chat_id to the user
            repo.use_telegram_registration_code(code, chat_id)
            user = repo.get_user(reg["user_id"])
            user_name = user.get("name", "User") if user else "User"

            # Log the event
            repo.create_agent_log(
                agent_name="telegram_listener",
                status="info",
                message=f"Telegram linked: user {reg['user_id']} ({user_name}) → chat_id {chat_id}",
                data={"event": "register", "user_id": reg["user_id"], "chat_id": chat_id},
            )

            logger.info("Telegram registered: user_id=%s chat_id=%s", reg["user_id"], chat_id)
            _reply(token, chat_id, (
                f"✅ <b>Linked successfully!</b>\n\n"
                f"Hello <b>{user_name}</b> — your Telegram is now connected to Agent Concierge.\n\n"
                "You can now send me queries. Phase B (read commands) and "
                "Phase C (write commands) are coming soon!"
            ))
            return

        # ── /unregister ───────────────────────────────────────────────────────
        if text.lower().startswith("/unregister"):
            user = repo.get_user_by_telegram_chat_id(chat_id)
            if not user:
                _reply(token, chat_id, "ℹ️ This Telegram account is not linked to any Agent Concierge account.")
                return

            repo.clear_user_telegram_chat_id(user["id"])
            repo.create_agent_log(
                agent_name="telegram_listener",
                status="info",
                message=f"Telegram unlinked: user {user['id']} ({user.get('name','')}) → chat_id {chat_id}",
                data={"event": "unregister", "user_id": user["id"], "chat_id": chat_id},
            )
            logger.info("Telegram unregistered: user_id=%s chat_id=%s", user["id"], chat_id)
            _reply(token, chat_id, (
                "✅ <b>Unlinked successfully.</b>\n\n"
                "Your Telegram account has been disconnected from Agent Concierge.\n"
                "You can re-link anytime from <b>Settings → Telegram Integration</b>."
            ))
            return

        # ── /whoami ───────────────────────────────────────────────────────────
        if text.lower().startswith("/whoami"):
            user = repo.get_user_by_telegram_chat_id(chat_id)
            if not user:
                _reply(token, chat_id, (
                    "❓ This Telegram account is not linked to any Agent Concierge account.\n\n"
                    "Use <code>/start</code> to see how to link your account."
                ))
            else:
                role_label = {
                    "admin": "Admin",
                    "it_manager": "IT Manager",
                    "finance_manager": "Finance Manager",
                    "employee": "Employee",
                }.get(user.get("role", ""), user.get("role", "Unknown"))
                registered_at = user.get("telegram_registered_at", "")
                date_str = registered_at[:10] if registered_at else "unknown date"
                _reply(token, chat_id, (
                    f"👤 <b>You are linked to:</b>\n"
                    f"Name: {user.get('name', '—')}\n"
                    f"Email: {user.get('email', '—')}\n"
                    f"Role: {role_label}\n"
                    f"Linked since: {date_str}"
                ))
            return

        # ── /cancel — abort active slot-filling session (Phase C.1) ─────────────
        if text.lower().startswith("/cancel"):
            user = repo.get_user_by_telegram_chat_id(chat_id)
            if not user:
                _reply(token, chat_id, "ℹ️ Nothing to cancel.")
                return
            from app.services.telegram_state import get_session, clear_session
            session = get_session(user["id"])
            if session:
                clear_session(user["id"])
                _reply(token, chat_id, "❌ Cancelled. Nothing was created.")
            else:
                _reply(token, chat_id, "ℹ️ Nothing to cancel.")
            return

        # ── /summary — daily snapshot (Phase B) ──────────────────────────────
        if text.lower().startswith("/summary"):
            user = repo.get_user_by_telegram_chat_id(chat_id)
            if not user:
                _reply(token, chat_id, (
                    "❓ Please link your account first.\n"
                    "Use <code>/start</code> to learn how."
                ))
                return
            from app.services.telegram_router import handle_telegram_message
            handle_telegram_message(user, "daily summary", token, chat_id, database_path)
            return

        # ── /help — list available commands (Phase B) ─────────────────────────
        if text.lower().startswith("/help"):
            user = repo.get_user_by_telegram_chat_id(chat_id)
            if not user:
                _reply(token, chat_id, (
                    "👋 <b>Agent Concierge Bot</b>\n\n"
                    "Commands: /start /register /unregister\n\n"
                    "Link your account to unlock full query access."
                ))
                return
            from app.services.telegram_router import handle_telegram_message
            handle_telegram_message(user, "help", token, chat_id, database_path)
            return

        # ── Any other message — Phase B / C router ───────────────────────────
        user = repo.get_user_by_telegram_chat_id(chat_id)
        if not user:
            _reply(token, chat_id, (
                "👋 Hi! I'm the Agent Concierge bot.\n\n"
                "To use me, link your Telegram to your web-app account:\n\n"
                "1. Log into the web app\n"
                "2. Go to <b>Settings → Telegram Integration</b>\n"
                "3. Click <b>Connect Telegram</b> and follow the instructions\n\n"
                "Or send /start for more details."
            ))
        else:
            # Phase C.3: intercept 4-8 digit messages when PIN entry is pending
            import re as _re
            if _re.match(r"^\d{4,8}$", text):
                from app.services.telegram_state import get_pending_pin_entry
                if get_pending_pin_entry(user["id"]):
                    from app.services.telegram_router import handle_pin_entry
                    handle_pin_entry(user, text, token, chat_id, database_path)
                    return
            # Phase B+: route through the Conci AI intent pipeline
            from app.services.telegram_router import handle_telegram_message
            handle_telegram_message(user, text, token, chat_id, database_path)

    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram handle_update error: %s", exc, exc_info=True)


# ── Polling loop ──────────────────────────────────────────────────────────────

def _poll_loop(token: str, database_path: str, stop: threading.Event) -> None:
    """Main long-polling loop. Runs in a daemon thread. Never propagates exceptions."""
    logger.info("Telegram listener started — polling getUpdates")
    offset: int | None = None

    # On startup, skip existing backlog by fetching current offset
    try:
        result = _tg_get(token, "getUpdates", timeout=1, limit=1, offset=-1)
        if result.get("ok") and result.get("result"):
            last = result["result"][-1]
            offset = last["update_id"] + 1
            logger.info("Telegram listener: skipped backlog, starting at offset %s", offset)
        elif result.get("ok"):
            logger.info("Telegram listener: no backlog, starting fresh")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram listener: failed to fetch initial offset: %s", exc)

    while not stop.is_set():
        try:
            params: dict[str, Any] = {"timeout": 20, "limit": 50}
            if offset is not None:
                params["offset"] = offset

            result = _tg_get(token, "getUpdates", **params)

            if not result.get("ok"):
                err = result.get("error", "unknown")
                # 409 = another getUpdates call is running — wait and retry
                if "409" in str(err):
                    logger.warning("Telegram listener: 409 conflict — another bot instance running?")
                    stop.wait(5)
                    continue
                logger.debug("Telegram getUpdates non-ok: %s", err)
                stop.wait(3)
                continue

            updates = result.get("result", [])
            for update in updates:
                update_id = update.get("update_id", 0)
                if offset is None or update_id >= offset:
                    _handle_update(update, token, database_path)
                    offset = update_id + 1

        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram listener poll error: %s — retrying in 5s", exc)
            stop.wait(5)

    logger.info("Telegram listener stopped")


# ── Public start / stop API ───────────────────────────────────────────────────

def start_listener(database_path: str) -> None:
    """Start the Telegram listener if enabled and configured.

    Called from FastAPI startup. Safe to call multiple times (idempotent).
    Never raises.
    """
    global _stop_event, _listener_thread

    try:
        enabled = os.environ.get("TELEGRAM_LISTENER_ENABLED", "").strip().lower()
        if enabled not in ("true", "1", "yes"):
            logger.info("Telegram listener disabled (TELEGRAM_LISTENER_ENABLED not set to true)")
            return

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            logger.warning("Telegram listener: TELEGRAM_BOT_TOKEN not set — listener not started")
            return

        if _listener_thread and _listener_thread.is_alive():
            logger.info("Telegram listener already running — skipping start")
            return

        _stop_event = threading.Event()
        _listener_thread = threading.Thread(
            target=_poll_loop,
            args=(token, database_path, _stop_event),
            name="telegram-listener",
            daemon=True,  # thread dies when main process exits
        )
        _listener_thread.start()
        logger.info("Telegram listener thread started (daemon=True)")

        # Print env-var instructions for user on first start
        bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "<YOUR_BOT_USERNAME>")
        logger.info(
            "Telegram bot username: @%s — "
            "Add TELEGRAM_BOT_USERNAME=<username> to .env if not already set",
            bot_username,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram listener failed to start: %s", exc, exc_info=True)


def stop_listener() -> None:
    """Signal the listener thread to stop. Called from FastAPI shutdown. Never raises."""
    global _stop_event, _listener_thread
    try:
        if _stop_event:
            _stop_event.set()
        if _listener_thread and _listener_thread.is_alive():
            _listener_thread.join(timeout=3)
        logger.info("Telegram listener stopped")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram listener stop error: %s", exc)


def is_running() -> bool:
    """Return True if the listener thread is alive."""
    return bool(_listener_thread and _listener_thread.is_alive())
