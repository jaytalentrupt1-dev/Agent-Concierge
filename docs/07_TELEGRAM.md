# Telegram Integration — Agent Admin-IT

---

## Configuration

| Setting | Value |
|---------|-------|
| Send function | `send_telegram_sync(text: str)` in `backend/app/services/telegram_service.py` |
| Bot token env var | `TELEGRAM_BOT_TOKEN` |
| Chat ID env var | `TELEGRAM_CHAT_ID` |
| Parse mode | HTML |
| Test endpoint | `POST /api/telegram/test` (Admin only) |

If `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are missing/blank, sends fail silently — a warning is logged but the agent run or action that triggered the send is **not** interrupted.

---

## What Triggers Telegram Messages

| Trigger | Message format |
|---------|---------------|
| `ticket_watchdog` success | `🎫 <b>Ticket Watchdog</b>\n{summary}` |
| `expense_monitor` success | `💰 <b>Expense Monitor</b>\n{summary}` |
| `inventory_monitor` success | `📦 <b>Inventory Monitor</b>\n{summary}` |
| `daily_briefing` success | `📋 <b>Daily Briefing</b>\n{summary}` |
| Conci AI creates a ticket | `🎫 <b>New Ticket Created</b>\nID: …\nTitle: …\nCategory: …\nPriority: …\nBy: …` |
| Test button in Agents dashboard | `✅ <b>Conci Agent Test</b>\nTelegram integration confirmed from Agent Concierge.` |

---

## Usage in Code

```python
# Simple send (used by agents):
from app.services.telegram_service import send_telegram_sync
result = send_telegram_sync("HTML text here")
# result: {"ok": True} or {"ok": False, "error": "..."}

# In agents (scheduler.py):
tg = send_telegram_sync(f"🎫 <b>Ticket Watchdog</b>\n{summary}")
if not tg.get("ok"):
    logger.warning("Telegram send failed: %s", tg.get("error"))

# In action_handler.py (after ticket creation):
send_telegram_sync(f"🎫 <b>New Ticket Created</b>\n...")
```

---

## Frontend Test Button

Located on the Agents dashboard (`/agents`). Calls `testTelegram()` from `api.js`:
```js
export function testTelegram() {
  return request("/api/telegram/test", { method: "POST" });
}
```
Shows toast: "📨 Telegram test message sent successfully!" or error detail.
