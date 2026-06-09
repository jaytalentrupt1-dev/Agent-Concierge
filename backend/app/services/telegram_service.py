"""Lightweight Telegram notification helper.

Reads credentials from environment variables:
  TELEGRAM_BOT_TOKEN — the bot token from BotFather
  TELEGRAM_CHAT_ID   — the chat/group ID to send messages to

Both can also be passed explicitly. If neither source is available the
call is silently skipped and ``{"ok": False, "error": "not_configured"}``
is returned — nothing is raised.
"""
from __future__ import annotations

import logging
import os
import urllib.request
import urllib.error
import urllib.parse
import json

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_sync(
    text: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict:
    """Send *text* to a Telegram chat.

    Parameters
    ----------
    text:       The message body. Supports HTML tags: <b>bold</b>, <i>italic</i>,
                <code>code</code>. Do NOT use Markdown (*bold*) — underscores in
                identifiers like agent_name will cause Telegram to reject the message.
    bot_token:  Override the TELEGRAM_BOT_TOKEN env var.
    chat_id:    Override the TELEGRAM_CHAT_ID env var.

    Returns a dict ``{"ok": True}`` on success or
    ``{"ok": False, "error": "<reason>"}`` on any failure.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    # Debug: log credential presence (never log full token)
    logger.info(
        "Telegram send attempt — token: %s, chat_id: %s",
        (token[:10] + "…") if token else "<not set>",
        cid if cid else "<not set>",
    )

    if not token or not cid:
        logger.warning("Telegram not configured — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env")
        return {"ok": False, "error": "not_configured"}

    url = _TELEGRAM_API.format(token=token)
    payload = json.dumps({
        "chat_id": cid,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            logger.info("Telegram API response: %s", body)
            if body.get("ok"):
                logger.info("Telegram message sent successfully to chat %s", cid)
                return {"ok": True}
            err = body.get("description", "unknown_error")
            logger.warning("Telegram API returned not-ok: %s", err)
            return {"ok": False, "error": err}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.warning("Telegram HTTP %s error: %s — %s", exc.code, exc.reason, body_text)
        return {"ok": False, "error": f"http_{exc.code}: {body_text}"}
    except urllib.error.URLError as exc:
        logger.warning("Telegram URL error: %s", exc.reason)
        return {"ok": False, "error": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram unexpected error: %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


# ── Phase C.2 additions — inline button support ───────────────────────────────
# These functions are NEW. The existing send_telegram_sync above is untouched.

_SEND_MESSAGE_API = "https://api.telegram.org/bot{token}/sendMessage"
_EDIT_MESSAGE_API = "https://api.telegram.org/bot{token}/editMessageText"
_ANSWER_CBQ_API   = "https://api.telegram.org/bot{token}/answerCallbackQuery"


def _bot_post(url: str, payload: dict) -> dict:
    """Internal POST helper — mirrors the pattern in send_telegram_sync."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            logger.warning("Telegram API not-ok: %s", body.get("description"))
        return body
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.warning("Telegram HTTP %s: %s", exc.code, body_text)
        return {"ok": False, "error": f"http_{exc.code}: {body_text}"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram post error: %s", exc)
        return {"ok": False, "error": str(exc)}


def send_telegram_with_buttons(
    chat_id: int | str,
    text: str,
    keyboard: dict,
    bot_token: str | None = None,
) -> dict:
    """Send a message with an inline keyboard (reply_markup).

    Parameters
    ----------
    chat_id:   Telegram chat ID to send to.
    text:      HTML-formatted message body.
    keyboard:  dict with key "inline_keyboard" — output of telegram_buttons helpers.
    bot_token: Override TELEGRAM_BOT_TOKEN env var.

    Returns {"ok": True, "message_id": int} on success or {"ok": False, "error": ...}.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("send_telegram_with_buttons: TELEGRAM_BOT_TOKEN not set")
        return {"ok": False, "error": "not_configured"}
    url = _SEND_MESSAGE_API.format(token=token)
    result = _bot_post(url, {
        "chat_id":      chat_id,
        "text":         text,
        "parse_mode":   "HTML",
        "reply_markup": keyboard,
    })
    if result.get("ok") and result.get("result"):
        return {"ok": True, "message_id": result["result"].get("message_id")}
    return result


def edit_telegram_message(
    chat_id: int | str,
    message_id: int,
    text: str,
    keyboard: dict | None = None,
    bot_token: str | None = None,
) -> dict:
    """Edit an existing bot message (text + optionally replace/remove buttons).

    Pass keyboard=None to leave existing markup unchanged, or pass
    telegram_buttons.remove_keyboard() to strip all buttons.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"ok": False, "error": "not_configured"}
    url = _EDIT_MESSAGE_API.format(token=token)
    payload: dict = {
        "chat_id":    chat_id,
        "message_id": message_id,
        "text":       text,
        "parse_mode": "HTML",
    }
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    return _bot_post(url, payload)


def answer_callback_query(
    callback_query_id: str,
    text: str = "",
    bot_token: str | None = None,
) -> dict:
    """Acknowledge a Telegram button click (clears the loading spinner).

    Must be called within 10 s of the click; Telegram drops stale acks silently.
    Pass a short text to show a pop-up notification to the user (optional).
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"ok": False, "error": "not_configured"}
    url = _ANSWER_CBQ_API.format(token=token)
    payload: dict = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]  # Telegram cap
    return _bot_post(url, payload)
