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
| `/summary` | Role-aware daily snapshot (Phase B) |
| `/help` | Lists all supported read commands (Phase B) |
| Any free-text | Classified by Conci AI → fetch + format (Phase B). Writes refused. |

### Phase C.1 — create_ticket via slot-filling

Send "create ticket" (or "new ticket", "raise ticket") to start a guided flow:

```
User:  create a ticket
Bot:   🎫 Let's create a ticket, Admin.
       What should the title be?  (Send /cancel to stop.)

User:  Laptop screen broken
Bot:   What category? (e.g. Hardware, Software, General)

User:  Hardware
Bot:   What priority? (Low / Medium / High)

User:  High
Bot:   Which branch? (Pune / Ahmedabad / Vadodara / Noida)

User:  Pune
Bot:   Please confirm this ticket:
       Title: Laptop screen broken
       Category: Hardware
       Priority: High
       Branch: Pune
       Reply yes to create or no to cancel.

User:  yes
Bot:   ✅ Ticket created!
       ID: #IT-1015
       Title: Laptop screen broken
       Status: Open
       Branch: Pune
       View in the web app for full details.
```

- Sessions are in-memory with a **30-minute idle timeout**
- Send `/cancel` at any point to abort
- All other Telegram commands (/start, /help, etc.) still work mid-flow (handled by listener before router)
- Session state is independent of Conci AI sidebar state

### Phase C.2 — approve/reject expense + close ticket via inline buttons

Send "approve expense EXP-1001" (or "reject expense EXP-1001", "close ticket IT-1013"):

```
User:  approve expense EXP-1001
Bot:   Approve or reject this expense?

       ID: EXP-1001
       Amount: Rs.12,450
       Category: Travel
       Submitted by: Shivam Raj
       Status: Pending Approval

       [✅ Approve]  [❌ Reject]
       [🚫 Cancel]

User: [clicks ✅ Approve]
Bot:  ✅ EXP-1001 approved.
```

Typed fallback (no button click needed):
```
User:  approve expense EXP-1002
Bot:   [confirmation message with buttons]
User:  yes
Bot:   ✅ EXP-1002 approved.    ← message updates, buttons removed
```

- `approve_expense` / `reject_expense` → `admin` or `finance_manager` only
- `close_ticket` → `admin` or `it_manager` only
- Double-click safe: second button press shows "already approved" from ToolExecutor
- Old message (>48h) edit failure falls back to a fresh reply
- All actions logged to `agent_logs` with `via: "button_or_typed"` field

#### Callback data format (≤ 64 bytes)

| Action | callback_data |
|--------|---------------|
| Approve expense | `exp:approve:{expense_id}` |
| Reject expense | `exp:reject:{expense_id}` |
| Close ticket | `tkt:close:{ticket_id}` |
| Cancel | `cancel:{entity_id}` |

#### New files added
- `backend/app/services/telegram_buttons.py` — keyboard builders + `parse_callback_data`
- New functions in `telegram_service.py`: `send_telegram_with_buttons`, `edit_telegram_message`, `answer_callback_query`

### Phase B — Read commands

Free-text is classified by `ConciAgentIntentService.classify()` then executed via `ToolExecutor` with the linked user's role for filtering.

**Supported intents:** `open_tickets`, `my_tickets`, `recent_tickets`, `open_tasks`, `my_tasks`, `overdue_tasks`, `pending_approvals`, `pending_expenses`, `expense_summary`, `active_vendors`, `vendor_billing`, `inventory_summary`, `inventory_in_use`, and more.

**Write intents** (`create_ticket`, `approve_expense`, etc.) return: *"I can't make changes from Telegram yet — Phase C is coming."*

**Unsupported text** returns: help suggestions.

All queries logged to `agent_logs` with `agent_name="telegram_router"`.

### Response format

HTML parse mode. Responses are capped at 10 items and split at 4096 chars if needed.

**Example — "recent tickets":**
```
🎫 Recent Tickets (10)

• IT-1013 — test ticket for slot filling
  Overdue · high · Noida
• IT-1012 — laptop screen broken
  Overdue · high · Pune
...

Open the web app for full details.
```

**Example — "/summary" (admin):**
```
📊 Today's Summary

🎫 Open Tickets: 0 (13 overdue)
✅ Open Tasks: 3 (6 overdue)
💰 Pending Expenses: 1

Updated: 2026-06-08 16:29 UTC
```

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
