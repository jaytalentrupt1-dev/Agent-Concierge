# Change Log — Agent Admin-IT

Newest entries first. Add a new row at the top after every code change.

---

### 2026-06-09 — Settings page rebuild (4-section design)
**Files:** `frontend/src/App.jsx`, `frontend/src/styles/globals.css`
**Why:** Replace legacy Settings page (multi-component, real CRUD) with a clean 4-section layout that matches the design system
**What:**
- `SettingsView` fully replaced — no new components, all logic inline
- Section 1 — Connectors: Email + WhatsApp rows in a table; all actions (Connect/Configure, Send Test, Disconnect, gear, 3-dot) → "Coming soon" toast
- Section 2 — Telegram Integration: real Phase A functionality inlined (no longer using `<TelegramPanel />`); register-code display with polling every 3s; disconnect; connected state with date + bot link
- Section 3 — Telegram PIN: renders `<TelegramPinPanel />` (Phase C.3, unchanged) only when `tgRegistered === true`
- Section 4 — Users (admin-only): display-only table with search; Add User, Filter, Edit, Delete, role-change dropdown, More → "Coming soon" toast
- CSS added: `.settings-card`, `.settings-card-header`, `.settings-card-title`, `.settings-card-subtitle`, `.settings-icon-wrap (.sm)`, `.settings-logs-pill`, `.settings-connector-name`, `.settings-connector-sub`, `.settings-status-chip (.not-connected/.mock-mode/.connected)`, `.settings-status-dot (variants)`, `.settings-action-cell`, `.settings-connector-actions`, `.connector-toast (.ok/.err)` — all with dark + light mode overrides
- `TelegramPanel` component remains in file (not called from SettingsView); `ConnectorsPanel`/`ConnectorConfigModal`/`UserManagement` remain in file (unused from SettingsView)
- All write-capable paths removed from SettingsView — no accidental CRUD exposure

---

### 2026-06-08 — Phase C.3: PIN security layer + remaining write intents via Telegram
**Files:** `admin_repository.py`, `telegram_state.py`, `main.py`, `telegram_router.py`, `telegram_listener.py`, `telegram_buttons.py`, `api.js`, `App.jsx`
**Why:** Security layer for all Telegram write actions; remaining write intents (create_task, mark_task_done, update_ticket, assign_ticket)
**What:**
- `admin_repository.py`: 4 new PIN columns on users table (`telegram_pin_hash`, `telegram_pin_set_at`, `telegram_pin_failed_attempts`, `telegram_pin_locked_until`); PBKDF2-HMAC-SHA256 helpers `_hash_pin`/`_verify_pin` (stdlib only); 4 new repo methods: `set_telegram_pin`, `clear_telegram_pin`, `get_telegram_pin_status`, `verify_telegram_pin` (lockout after 3 failures, 30-min lock; never logs PIN)
- `telegram_state.py`: new `PendingPinEntry` dataclass + store/get/clear with 5-min timeout
- `main.py`: 4 PIN endpoints — `POST /api/telegram/pin` (set), `PUT` (change, requires old PIN), `DELETE` (remove), `GET` (status)
- `telegram_router.py`: `require_pin_then_execute` central PIN gate (no PIN → execute directly; locked → reject; PIN set → store PendingPinEntry + prompt); `handle_pin_entry` verifies PIN + dispatches action; `_dispatch_write_action` maps intent → executor; C.1/C.2 retrofitted to call PIN gate; create_task slot-filling (title → assigned_role → due_date optional + /skip); mark_task_done button flow; update_ticket status + assign_ticket via regex
- `telegram_listener.py`: 4-8 digit message → if PendingPinEntry active → route to `handle_pin_entry` before normal routing
- `telegram_buttons.py`: `task_done_keyboard` (task:done:{id} + cancel)
- `api.js` + `App.jsx`: `TelegramPinPanel` Settings section with Set/Change/Remove PIN modals; `telegramPinStatus/SetPin/ChangePin/RemovePin` API functions
- PIN check on EVERY write — no exceptions; no PIN set → execute directly (opt-in security)
- Phase A/B/C.1/C.2/Conci AI/outbound alerts all untouched

---

### 2026-06-08 — Phase C.2: inline buttons + approve/reject expense + close ticket via Telegram
**Files:** `telegram_listener.py`, `telegram_buttons.py` (new), `telegram_service.py` (added `send_telegram_with_buttons`, `edit_telegram_message`, `answer_callback_query`), `telegram_router.py`, `telegram_state.py`
**Why:** Users need to approve/reject expenses and close tickets directly from Telegram without opening the web app
**What:**
- `telegram_listener.py`: added `callback_query` path in `_handle_update` — extracts `callback_query_id`, looks up user by `telegram_chat_id`, calls `answer_callback_query` to dismiss spinner, routes to `handle_callback`
- `telegram_buttons.py` (new): `expense_approval_keyboard`, `ticket_close_keyboard`, `remove_keyboard`, `parse_callback_data` — all callback_data strings stay under 64 bytes
- `telegram_service.py`: added `send_telegram_with_buttons` (sendMessage + reply_markup), `edit_telegram_message` (editMessageText), `answer_callback_query` (answerCallbackQuery). Existing `send_telegram_sync` untouched.
- `telegram_router.py`: added `handle_callback` dispatcher; `_send_expense_confirmation` / `_send_ticket_close_confirmation` helpers; `_execute_action_and_edit` (calls existing ToolExecutor, edits message, fires outbound alert); text-based triggers via `_RE_APPROVE/_RE_REJECT/_RE_CLOSE` regex; typed yes/no fallback checks `PendingConfirmation`; removed `approve_expense`/`ticket_status_update` from `_WRITE_INTENTS`; fixed missing `import os`; updated help text and expense formatter
- `telegram_state.py`: added `PendingConfirmation` dataclass + store/get/clear helpers (separate from slot-filling sessions, same 30-min timeout)
- Double-click safe: `clear_pending_confirmation` called before executing action; second click hits ToolExecutor which returns "already approved/rejected" error → shown gracefully
- All write actions logged to agent_logs with `via: "button_or_typed"` field
- Phase A, B, C.1, Conci AI sidebar, outbound alerts all untouched

---

### 2026-06-04 — Fixed: outbound Telegram alert fires after Telegram-initiated ticket creation
**Files:** `backend/app/services/telegram_router.py`
**Why:** Conci AI sidebar ticket creation fires `send_telegram_sync` alert; Telegram chat creation did not — inconsistent
**What:** Added same `send_telegram_sync` call (identical format to `action_handler._maybe_notify_telegram`) immediately after successful `create_ticket` in `_handle_slot_filling`. User still receives the "✅ Ticket created" chat reply first; outbound alert follows via `TELEGRAM_CHAT_ID` channel.

---

### 2026-06-04 — Phase C.1: create_ticket via Telegram (slot-filling + confirmation)
**Files:** `backend/app/services/telegram_state.py` (new), `backend/app/services/telegram_router.py`, `backend/app/services/telegram_listener.py`
**Why:** First Telegram write operation — users can create tickets via guided chat
**What:**
- New `telegram_state.py` — in-memory `TelegramSession` store keyed by user_id; 30-min idle timeout; lazy cleanup on `get_session()`
- `telegram_router.py`: session check at start of every message (intercepts non-command text); `create_ticket` removed from `_WRITE_INTENTS`; `_handle_slot_filling()` collects title → category → priority → branch; typed yes/no confirmation; real DB write via existing `ToolExecutor.create_ticket()`; `/cancel` mid-flow
- `telegram_listener.py`: `/cancel` command handler; `/help` updated with "create ticket" entry
- All events (session start, slots, confirm, success, cancel, error) logged to `agent_logs`
- Phase A, Phase B, outbound alerts untouched

---

### 2026-06-04 — Phase B: Telegram read commands via Conci AI brain
**Files:** `backend/app/services/telegram_router.py` (new), `backend/app/services/telegram_listener.py`
**Why:** Registered users can now query Agent Concierge data directly from Telegram chat
**What:**
- New `telegram_router.py` — routes free-text messages through `ConciAgentIntentService.classify()`, executes via existing `ToolExecutor`, formats results as HTML Telegram messages
- Supported read intents: tickets, tasks, expenses, vendors, inventory, travel; all role-filtered via ToolExecutor
- `/summary` command → role-aware daily snapshot (open tickets, overdue tasks, pending expenses)
- `/help` command → lists all available commands with role note
- Write intents (`create_ticket`, `approve_expense`, etc.) → politely refused with "Phase C coming"
- Unsupported intents → help text with suggestions
- All queries logged to `agent_logs` with `agent_name="telegram_router"`
- Responses split at 4096-char limit if needed
- Phase A commands (/start /register /unregister /whoami) unchanged

---

### 2026-06-04 — Two-way Telegram chat foundation (Phase A)
**Files:** `backend/app/services/telegram_listener.py` (new), `backend/app/repositories/admin_repository.py`, `backend/app/main.py`, `frontend/src/api.js`, `frontend/src/App.jsx`
**Why:** Enable users to query Agent Concierge via Telegram chat in addition to receiving outbound alerts
**What:**
- New `telegram_listener.py` — daemon thread polls `getUpdates` (long-polling); handles `/start`, `/register <code>`, `/unregister`, `/whoami`; Phase A placeholder reply for registered users
- DB: added `telegram_chat_id`, `telegram_registered_at` columns to `users` (auto-migrated); new `telegram_registration_codes` table (code, user_id, expires_at, used)
- New repository methods: `get_user_by_telegram_chat_id`, `set_user_telegram_chat_id`, `clear_user_telegram_chat_id`, `create_telegram_registration_code`, `get_telegram_registration_code`, `use_telegram_registration_code`
- New API endpoints: `POST /api/telegram/register/start`, `GET /api/telegram/registration/status`, `POST /api/telegram/unregister`
- FastAPI startup/shutdown hooks for listener (runs alongside scheduler)
- Settings page: new `TelegramPanel` component — STATE A (Connect + code display), STATE B (Connected + Disconnect), auto-polls every 5s while code is shown
- Outbound alerts (`telegram_service.py`) untouched

---

### 2026-06-03 — Fixed notification spam from background agents
**Files:** `backend/app/services/scheduler.py`, `backend/app/repositories/admin_repository.py`
**Why:** Agents re-created notifications every run for the same entities — expense_monitor (every 2h) was the worst offender (162 finance notifications); daily_briefing created admin notification unconditionally even when nothing happened
**What:**
- Added `notification_exists_for_entity(entity_type, entity_id, target_role, hours=24) → bool` helper to `AdminRepository`
- Wrapped all 4 alert-creation sites in `ticket_watchdog`, `expense_monitor`, `inventory_monitor` with 24h dedup guard
- Added `if open_tickets > 0 or overdue_tasks > 0 or pending_expenses > 0:` condition to `daily_briefing` admin notification
- One-time cleanup SQL: deleted 227 duplicate rows (261 → 34 kept)
- Verified: second `expense_monitor` run adds 0 rows; all 4 agents tested back-to-back

---

### 2026-06-03 — Light mode audit + fixes
**Files:** `frontend/src/styles/globals.css`, `frontend/src/App.jsx`
**Why:** Systematic sweep for light mode breakage; most components were already covered by `html:not([data-theme="dark"])` overrides, but 3 gaps found
**What:**
- Added `.conci-icon` light mode override (red tint `rgba(239,68,68,0.10)`) — was showing dark `#171717` circle on white panel header
- Added `.metric-icon` light mode override (red tint `rgba(239,68,68,0.08)`) — was showing legacy blue `#eef2ff` instead of red brand tint
- Made Recharts axis fills theme-aware (`#71717A` dark / `#52525B` light) in `DashboardBarChart` and `DashboardLineChart` via `axisColor` const
- Verified all other components already covered: tables, modals, forms, inputs, status pills, kpi cards, agents dashboard, login, notification panel, CustomSelect ✅

---

### 2026-06-03 — Investigated Notification Bell
**Files:** none (investigation only)
**Status:** Core bell is fully working (real data, polling, click handlers, mark-all). Three non-critical issues found: (1) daily_briefing creates admin notification unconditionally every run → 83/261 DB rows are admin spam; (2) no notification retention — limit=100 silently drops older rows; (3) read-all returns hardcoded unread_count=0 (safe but not recomputed). No broken endpoints, no hardcoded mock data, no missing API calls.

---

### 2026-06-03 — Fixed slot-filling regression: typo corrector + AI confidence override
**Files:** `backend/app/services/conci_agent.py`, `backend/app/services/action_handler.py`
**Why:** "test ticket for slot filling" → `_correct_token` rewrote "filling"→"billing" (score 0.857 ≥ old 0.78 threshold) → AI saw corrupted text "slot billing" → returned `vendor_billing` at hardcoded 0.9 confidence → abort guard fired → slot state wiped
**What (Option B):** Raised `_correct_token` threshold 0.78 → 0.90. Single-char differences no longer trigger correction; real typos (score ≥ 0.91) still corrected.
**What (Option C-2):** Added `classification_source: str` field to `IntentResult` (`"strong_rule"` / `"local"` / `"ai"`). Extended abort guard to `source != "ai"` — pure AI classifications cannot abort slot-filling. `classify()` re-checks the strong rule when `openai_intent` is given, so `chatbot_priority_local_intent`-routed intents retain their `"strong_rule"` source and can still pivot correctly. Updated SLOT DEBUG log to include source field.

---

### 2026-06-03 — Added branch as required 4th slot in create_ticket flow
**Files:** `backend/app/services/conversation_state.py`
**Why:** Branch was silently defaulting to "Pune" in ToolExecutor; users had no way to set it via Conci AI
**What:** Added `"branch"` to `REQUIRED_FIELDS["create_ticket"]` (slot order: title → category → priority → branch → confirm → create). Added branch prompt `"Which branch? (Pune / Ahmedabad / Vadodara / Noida)"` to `FIELD_PROMPTS`. No other files changed — slot loop and `ToolExecutor.create_ticket()` already handle branch generically.

---

### 2026-06-03 — Fixed Conci AI create_ticket slot-filling bug
**Files:** `backend/app/services/action_handler.py`
**Why:** Abort guard was too broad — any classifier hit ≥ 0.58 (including slot values like "Laptop screen broken" → `inventory_summary`) wiped slot state mid-flow
**What:**
- Added `import logging` + `logger = logging.getLogger(__name__)` to `action_handler.py`
- Defined `_SLOT_ABORT_INTENTS` frozenset (29 fetch / pivot intents) — only these can clear active slot state
- Replaced old broad guard with `if intent in _SLOT_ABORT_INTENTS and intent != state.intent and confidence >= 0.85`
- Confidence floor (0.85) blocks fuzzy false-positives; `intent_result["confidence"]` is already present via `to_dict()`
- Added `logger.debug` at both `clear_state()` call-sites for observability (Fix C)
- Updated `docs/04_AGENTS.md` with whitelist details, `docs/09_STATUS.md` moved bug to ✅

---

### 2026-06-03 — Investigated Conci AI create_ticket slot-filling bug (no code changed)
**Files:** none (investigation only)
**Why:** Bug reported — slot-filling aborts when slot values trigger the intent classifier
**What:** Traced full broken flow; root cause confirmed at `action_handler.py:91` — abort guard fires on any classifier hit ≥ 0.58 including slot values like "laptop"; secondary issue at `main.py:2425`; `ConciAISidebar.jsx` confirmed not to exist (Conci AI is inline in `App.jsx`); fix approach proposed in `09_STATUS.md`.

---

## Format

```
### YYYY-MM-DD — Short title
**Files:** list of files touched
**Why:** one-line reason
**What:** brief description of change
```

---

### 2026-06-03 — Split PROJECT_CONTEXT.md into /docs folder
**Files:** `docs/` (12 new files), `PROJECT_CONTEXT.md` (replaced with pointer)
**Why:** 1362-line context file was eating too much context window on every session
**What:** Created `docs/00_INDEX.md` through `docs/11_RULES.md`. PROJECT_CONTEXT.md now just points to the index.

---

### 2026-06-03 — Fixed agent toggle switches (pause/resume APScheduler)
**Files:** `backend/app/services/scheduler.py`, `backend/app/main.py`, `frontend/src/api.js`, `frontend/src/components/AgentsDashboard.jsx`, `frontend/src/styles/globals.css`
**Why:** Toggle was only flipping local React state — agents kept running regardless of what the toggle showed
**What:**
- Added `pause_job(job_id)` and `resume_job(job_id)` helpers to `scheduler.py`
- Added `PATCH /api/agents/{agent_name}/toggle` endpoint (admin-only, logs to `agent_logs`)
- Added `"paused": bool` field to `GET /api/agents/status` response
- Fixed `AgentCard` to initialise `enabled` from `agent.paused !== true` (not hardcoded `true`)
- Toggle now calls `toggleAgent()` API with optimistic update + error revert
- Added amber `.am-status-pill.paused` CSS class
- Status pill now shows "Running" or "Paused" dynamically

---

### 2026-06-03 — Added PROJECT_CONTEXT.md maintenance rule + AGENT SYSTEM + TELEGRAM sections
**Files:** `PROJECT_CONTEXT.md`
**Why:** File lacked dedicated sections for agent system, Telegram, and a change log
**What:** Added CHANGE LOG table, AGENT SYSTEM section (agents table, toggle behaviour, scheduler lifecycle), TELEGRAM INTEGRATION section, updated endpoints list, updated known bugs, added Current Status ✅/❌ section, added new files to the Important Files section

---

### 2026-05-22 — Multi-branch support
**Files:** `backend/app/main.py`, `backend/app/repositories/admin_repository.py`, `frontend/src/App.jsx`, multiple component files
**Why:** Support Pune / Ahmedabad / Vadodara / Noida office branches
**What:** Added `branch` field to Vendors, Inventory, Tickets, Expenses, Travel. All add/edit forms include branch dropdown. All list endpoints accept `?branch=` query param. Conci AI understands branch-specific questions. Old rows default to Pune.

---

### 2026-05-22 — Full dark/red UI overhaul
**Files:** `frontend/src/styles/globals.css`, `frontend/src/App.jsx`
**Why:** Match Agent Concierge reference UI
**What:** `#0A0A0A` bg, `#EF4444` red accent, SearchBar component, notification bell animations, pill-shaped sun/moon theme toggle, Conci AI sidebar restyle, global micro-interactions, all blue/purple → red conversions.
