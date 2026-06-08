# Current Status — Agent Admin-IT

---

## Done ✅

- Full Auth system (demo, sessionStorage bearer tokens, role-based nav)
- Dashboard — role-based command centre (Admin / IT Manager / Finance Manager / Employee)
- Vendors — Admin CRUD + Finance read-only + billing normalization
- Tasks — all roles, role-scoped, with assignment notifications
- Tickets — all roles, role-scoped, unified IT+Admin directory
- Travel & Calendar — Admin + Finance, SQLite-backed, analytics, Google placeholder fields
- Expenses — Admin + Finance, CSV/XLSX import with preview/confirm
- Inventory — Admin + IT Manager, bulk ops, import batches, status updates
- Reports — Admin + IT + Finance, file upload/download/preview
- Settings — Profile, Connectors (Email/WhatsApp), User Management (Admin)
- **Agents dashboard** — live APScheduler monitoring, toggle pause/resume, Run Now, logs modal
- **Agent toggle fix** — toggle actually pauses/resumes APScheduler jobs (was only local state before)
- **Conci AI slot-filling fix** — whitelist-based abort guard; slot values no longer trigger false pivot-detection mid-flow
- **Notification bell** — verified working with real data (polling, click handlers, mark-all); 24h dedup added to agents; spam cleaned (261 → 34 → 37 rows)
- **Telegram Phase A** — two-way listener foundation: registration flow, /start /register /unregister /whoami, Settings UI panel, 3 API endpoints, DB migration
- Telegram notifications on every agent run + Conci AI ticket creation
- Conci AI chat panel — role-scoped, DeepInfra/OpenAI/local fallback, file upload, table responses
- Multi-branch support — Pune / Ahmedabad / Vadodara / Noida across all major modules
- Dark/red theme + light mode (fully audited and verified 2026-06-03 — all pages, components, tables, modals, forms, status pills)
- Notification bell — real unread count, role-scoped, per-user read state

---

## Pending ❌

- ~~**Conci AI slot-filling bug**~~ — **Fixed 2026-06-03** (whitelist-based abort guard in `action_handler.py`)
- **Telegram Phase B** — read commands via Telegram chat (show my tickets, expenses, etc.)
- **Telegram Phase C** — write commands via Telegram chat (create ticket, approve expense, etc.)
- Agent pause state persistence across backend restarts (currently in-memory only)
- Real Google Calendar / Gmail integration (OAuth scaffold exists, not wired end-to-end)
- Real WhatsApp / Twilio integration (mock mode only)
- Real email — SMTP/SendGrid paths exist but default to mock mode
- Production auth (SSO, password hashing, secure sessions, RBAC)
- Docker / deployment setup
- Frontend unit tests / browser E2E tests
- Database migration framework (currently `CREATE TABLE IF NOT EXISTS` + lightweight compat patches)
- Vendor delete, contract renewal workflows
- Purchase/reorder automation for Inventory
- README documentation for `VITE_API_BASE_URL`

---

## Known Bugs

### ✅ Conci AI `create_ticket` slot-filling — FIXED 2026-06-03
**File:** `backend/app/services/action_handler.py`
**What was fixed:** Replaced the broad abort guard (`intent != "unsupported" and intent != state.intent`) with a `_SLOT_ABORT_INTENTS` whitelist. Slot values like "Laptop screen broken" no longer trigger false pivot detection mid-flow. Added `logger.debug` at every `clear_state()` call for observability.
**Remaining / not fixed:** Secondary issue at `main.py:2425` (`chatbot_agent_response_for` unconditional fallback) is still present but rarely triggers now that the primary abort is fixed.

### 🟡 Agent pause state lost on server restart
**Symptom:** Paused agents resume automatically if the backend process restarts.
**Root cause:** `_conversation_store` and APScheduler state are both in-memory; not persisted to DB.
**Fix approach:** Persist pause state in a new `agent_config` table; restore on scheduler start.

### 🟡 Single-tab sessionStorage token
**Symptom:** Opening the app in a new tab or incognito shows the login screen (expected), but sharing links cross-tab doesn't work.
**Root cause:** By design (sessionStorage is per-tab). Trade-off: prevents stale shared-link auto-login.

---

## Last Test Results

| Suite | Result |
|-------|--------|
| Backend pytest | 190 passed |
| Frontend build (`npm run build`) | ✅ passes |
| vendorBilling.test.mjs | ✅ passes |
| navigationAccess.test.mjs | ✅ passes |
