# Change Log — Agent Admin-IT

Newest entries first. Add a new row at the top after every code change.

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
