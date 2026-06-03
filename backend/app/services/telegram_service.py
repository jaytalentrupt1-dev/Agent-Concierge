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
