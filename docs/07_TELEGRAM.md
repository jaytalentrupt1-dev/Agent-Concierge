# Telegram Integration — Agent Admin-IT

---

## Architecture

Two independent subsystems share the same bot token:

| Subsystem | File | Direction | Trigger |
|-----------|------|-----------|---------|
| **Outbound alerts** | `telegram_service.py` | App → Telegram | Agent runs, ticket creation |
| **Two-way listener** | `telegram_listener.py` | Telegram → App → Telegram | User sends message to bot (Phase A+) |

---

## Configuration

| Setting | Value |
|---------|-------|
| Send function | `send_telegram_sync(text: str)` in `backend/app/services/telegram_service.py` |
| Bot token env var | `TELEGRAM_BOT_TOKEN` |
| Chat ID env var (outbound) | `TELEGRAM_CHAT_ID` |
| Bot username env var | `TELEGRAM_BOT_USERNAME` (no @, e.g. `MyAgentBot`) |
| Listener enabled env var | `TELEGRAM_LISTENER_ENABLED=true` |
| Parse mode | HTML |
| Test endpoint | `POST /api/telegram/test` (Admin only) |

If `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are missing/blank, sends fail silently — a warning is logged but the agent run or action that triggered the send is **not** interrupted.

**To add to `.env` for two-way chat:**
```
TELEGRAM_BOT_USERNAME=YourBotUsernameWithoutAt
TELEGRAM_LISTENER_ENABLED=true
```

---

## Two-Way Listener (Phase A)

### Startup
On FastAPI startup, if `TELEGRAM_LISTENER_ENABLED=true` AND `TELEGRAM_BOT_TOKEN` is set, a daemon thread is started (`telegram-listener`). It polls `getUpdates` (long-polling, 20s timeout). On startup it skips the backlog by fetching the latest `update_id` first.

### Registration flow
Users must link their Telegram account to their web-app account before the bot responds to their queries:

1. User logs into web app → **Settings → Telegram Integration → Connect Telegram**
2. Backend generates a 6-digit one-time code (expires in 10 min) via `POST /api/telegram/register/start`
3. Frontend displays: `Open Telegram, send /register <code> to @BotName`
4. User sends `/register 123456` to the bot
5. Listener looks up code → links `telegram_chat_id` to `user_id` → replies success
6. Settings page auto-refreshes every 5s while code is shown → switches to STATE B (Connected)

### Commands handled

| Command | Response |
|---------|----------|
| `/start` | Welcome message + registration instructions |
| `/register <code>` | Runs registration flow; links chat to account |
| `/unregister` | Removes link; confirms unlinked |
| `/whoami` | Shows linked user name, role, linked-since date |
| Any other text | Registered: Phase A placeholder. Unregistered: registration instructions. |

### API endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/telegram/register/start` | `current_user` | Generate 6-digit code |
| GET | `/api/telegram/registration/status` | `current_user` | Check if linked |
| POST | `/api/telegram/unregister` | `current_user` | Remove link |

### Database tables added
- `users.telegram_chat_id INTEGER NULL` — the Telegram chat ID
- `users.telegram_registered_at TEXT NULL` — when linked
- `telegram_registration_codes` — one-time codes (code, user_id, expires_at, used)

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
