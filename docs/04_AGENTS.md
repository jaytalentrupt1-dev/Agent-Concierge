# Agent System — Agent Admin-IT

All agent code lives in `backend/app/services/scheduler.py`.
The scheduler is started on FastAPI `startup` and stopped on `shutdown` (wired in `main.py`).

---

## Registered Agents

| Agent ID | Schedule | What It Does |
|----------|----------|-------------|
| `ticket_watchdog` | Every 1 hour | Marks open tickets >48 h old as Overdue; auto-assigns unassigned tickets to `it_manager` (IT) or `admin` (Admin) |
| `expense_monitor` | Every 2 hours | Alerts Finance on pending expenses >72 h old or amount >₹1,00,000 |
| `inventory_monitor` | Every 6 hours | Flags assets with status "Submitted to Vendor" for >30 days |
| `daily_briefing` | Daily 8 AM UTC | Sends morning summary notification to Admin / IT Manager / Finance Manager; also sends Telegram message |

All agents write to `agent_logs` on success and on error.
All agents send a Telegram message on success (fails silently if Telegram is not configured).

### Notification deduplication (24h window)

`ticket_watchdog`, `expense_monitor`, and `inventory_monitor` all call
`repo.notification_exists_for_entity(entity_type, entity_id, target_role, hours=24)`
before calling `repo.add_notification()`. If a notification for the same entity/role
was already created within the last 24 hours, the new one is skipped.

`daily_briefing` sends an admin notification only when there is actionable activity
(`open_tickets > 0 or overdue_tasks > 0 or pending_expenses > 0`). IT and finance
notifications retain their original conditional guards.

Helper: `AdminRepository.notification_exists_for_entity(entity_type, entity_id, target_role, hours=24) → bool`

---

## Scheduler Lifecycle

```python
# backend/app/services/scheduler.py

start_scheduler(database_path: str)  # called on FastAPI startup
stop_scheduler()                      # called on FastAPI shutdown
pause_job(job_id: str) -> bool        # pauses one job; returns False if scheduler not running
resume_job(job_id: str) -> bool       # resumes one job; returns False if scheduler not running
```

The `_scheduler` global is a `BackgroundScheduler(timezone="UTC")` instance.
Job IDs match agent function names exactly: `"ticket_watchdog"`, `"expense_monitor"`, etc.

---

## Toggle API

### `PATCH /api/agents/{agent_name}/toggle`
- **Auth:** Admin only (`Depends(admin_user)`)
- **Body:** `{"enabled": true | false}`
- **enabled=false** → calls `pause_job(agent_name)` → APScheduler stops scheduling the job
- **enabled=true** → calls `resume_job(agent_name)` → APScheduler resumes the job
- Writes to `agent_logs`: `status="info"`, `message="paused by admin"` or `"resumed by admin"`, `data={"action": "toggle_off"|"toggle_on", "actor": email}`
- Returns: `{"ok": true, "agent": name, "paused": bool}`
- Error 503 if scheduler not running or job not found

### `GET /api/agents/status`
- Returns list of 4 agents, each with:
  - `name`, `schedule`, `last_run_at`, `last_status`, `last_message`
  - `next_run_at` — `null` when paused
  - `paused: bool` — `true` when `job.next_run_time is None` (job exists but paused)
  - `scheduler_running: bool`

### `POST /api/agents/run/{agent_name}`
- Immediately invokes the agent function directly (bypasses scheduler)
- Works regardless of whether the job is paused
- Writes to `agent_logs` via the agent function itself

### `GET /api/agents/logs`
- Query params: `agent_name` (optional), `limit` (default 50)
- Returns `agent_logs` rows newest-first

---

## Frontend — Agents Dashboard

**File:** `frontend/src/components/AgentsDashboard.jsx`
**Route:** `/agents` (Admin only)

### AgentCard toggle behaviour
```jsx
// State initialises from backend, not hardcoded
const [enabled, setEnabled] = useState(agent.paused !== true);

async function handleToggle() {
  const newEnabled = !enabled;
  setEnabled(newEnabled);          // optimistic update
  try {
    await toggleAgent(agent.name, newEnabled);
  } catch (err) {
    setEnabled(!newEnabled);       // revert on error
    setToast({ ok: false, msg: err.message });
  }
}
```

Status pill: green "Running" (`am-status-pill running`) / amber "Paused" (`am-status-pill paused`)

### api.js function
```js
export function toggleAgent(agentName, enabled) {
  return request(`/api/agents/${agentName}/toggle`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
}
```

---

## Important Caveat

**Pause state is in-memory only.** If the backend server restarts, all jobs resume automatically.
Pause state is NOT persisted to the database across restarts.

---

## Conci AI Slot-Filling (related, see also 08_FRONTEND.md)

Conci AI uses a separate slot-filling system for multi-turn conversations:
- `backend/app/services/action_handler.py` — intent → slot state → execution
- `backend/app/services/conversation_state.py` — in-memory store keyed by `user_id`
- `backend/app/services/tool_executor.py` — slot data → repository calls

### Abort guard (whitelist + confidence + source, fixed 2026-06-03, regression-fixed 2026-06-03)

Slot-filling is only aborted mid-flow when **all four** conditions hold:
1. The classifier fires an intent in `_SLOT_ABORT_INTENTS`
2. That intent differs from the current `state.intent`
3. Classifier confidence is **≥ 0.85**
4. `classification_source` is **not `"ai"`** — pure AI-sourced classifications are distrusted mid-slot-filling

#### `classification_source` field (added to `IntentResult`)

| Source | When set | Confidence | Trusted to abort? |
|--------|----------|------------|-------------------|
| `"strong_rule"` | Keyword rule fired (e.g. "vendor" + "billing" in tokens) | 0.96 | ✅ Yes |
| `"local"` | Phrase similarity ≥ 0.58 | 0.58–1.0 | ✅ Yes (if ≥ 0.85) |
| `"ai"` | OpenAI/DeepInfra via `openai_intent` shortcut, and strong rule does NOT independently agree | 0.9 (hardcoded) | ❌ No |

**Why `"ai"` is distrusted:** the typo corrector (`_correct_token`) runs before the AI sees the text. Words like "filling" can be silently rewritten to domain terms ("billing"), making an innocent slot value appear to be a new command to the AI.

**Special case:** When `chatbot_priority_local_intent` passes a local strong-rule result as `openai_intent`, `classify()` re-checks the strong rule. If it independently fires the same intent, the source is upgraded to `"strong_rule"` (not "ai"), so genuine pivots still abort correctly.

#### `_correct_token` threshold

Raised from **0.78 → 0.90** (in `conci_agent.py`). One-character differences (e.g. "filling"/"billing" at 0.857) no longer trigger correction. Real typos (e.g. "tiket"→"ticket" at 0.909, "vndor"→"vendor" at 0.909) still qualify. COMMON_TYPOS dict is unaffected.

Intents in `_SLOT_ABORT_INTENTS` (all fetch lookups + different create/update pivots):
- Ticket: `open_tickets`, `my_tickets`, `recent_tickets`, `ticket_status`, `ticket_status_update`
- Task: `open_tasks`, `my_tasks`, `overdue_tasks`
- Approvals / finance: `pending_approvals`, `vendor_billing`, `active_vendors`, `vendor_count`, `vendor_details`, `pending_expenses`, `expenses_by_month`, `expenses_by_category`, `expenses_last_month`, `expenses_this_month`
- Inventory: `inventory_summary`, `inventory_in_use`, `inventory_submitted_vendor`, `inventory_recent_updates`
- Travel / calendar: `travel_spend`, `travel_recent_records`, `calendar_events`
- Other: `reports`, `users_settings`, `help`
- New-flow pivots: `create_ticket` (restart), `create_task`, `create_vendor`

NOT in whitelist (would cause false aborts): `casual_identity`, `utility_date`, `utility_time`, `file_reading`

Every abort and confirmation-phase fallthrough emits a `logger.debug` line for observability.

---

### create_ticket slot order

`title` → `category` → `priority` → `branch` → confirm → create

Branch prompt: `"Which branch? (Pune / Ahmedabad / Vadodara / Noida)"`
Branch is a required slot (not defaulted). Defensive fallback `"Pune"` only fires in `ToolExecutor.create_ticket()` if the field is somehow absent after slot-filling (should never happen).
