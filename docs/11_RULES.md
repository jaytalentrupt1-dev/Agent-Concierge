# Strict Rules — Agent Admin-IT

Read this before writing any code. These rules must never be broken.

---

## Absolute Don'ts

| Rule | Detail |
|------|--------|
| ❌ Never modify `.env` | Environment file is local-only and must never be touched or committed |
| ❌ Never change existing endpoints | Only ADD new endpoints — never alter paths, methods, or response shapes of existing ones |
| ❌ Never break "Run Now" | `POST /api/agents/run/{agent_name}` must always work regardless of pause state |
| ❌ Never remove or alter the 4 agents | `ticket_watchdog`, `expense_monitor`, `inventory_monitor`, `daily_briefing` — schedules, logic, and IDs must stay intact |
| ❌ Never commit secrets | No API keys, passwords, tokens in any committed file |
| ❌ Never use `--no-verify` or `--no-gpg-sign` on git commands | |
| ❌ Never force-push to main/master | |

---

## Backend Conventions

- **Auth dependency:** Use `Depends(admin_user)` for admin-only routes, `Depends(current_user)` for authenticated routes
- **Admin check pattern** (inline): `if user.get("role") != "admin": raise HTTPException(status_code=403, ...)`
- **All routes** live inside the `create_app()` factory function in `backend/app/main.py`
- **Repository only** — no raw SQL outside `admin_repository.py`
- **Schema changes:** Add columns with `ALTER TABLE … ADD COLUMN … DEFAULT` or via compat repair in `init_schema()`. Never drop columns.
- **Error handling:** All new endpoints must have `try/except` with clear error messages
- **Logging:** Use `logger = logging.getLogger(__name__)` in each module
- **Pydantic schemas** for new request bodies go in `backend/app/models/schemas.py`

---

## Frontend Conventions

- **All API calls** go through `request()` in `frontend/src/api.js` — never use raw `fetch()` elsewhere
- **CSS override** goes in `frontend/src/styles/globals.css` (not `styles.css`)
- **Never hardcode state** that should come from the backend (the agent toggle bug was exactly this)
- **Optimistic updates** with revert on error for toggle/status actions
- **Toast pattern** for success/error feedback — use the existing `setToast({ ok, msg })` pattern
- **Icons:** `lucide-react` only — no other icon library
- **Theme colours:** use the established palette — `#EF4444` red accent, `#0A0A0A` bg, `#141414` cards
- **No inline styles** for layout — use CSS classes

---

## Documentation Maintenance Rule

After **every** task that touches code:

1. Update only the affected `docs/` file(s) — do NOT rewrite unrelated sections
2. Prepend a new entry to `docs/10_CHANGELOG.md` using the standard format
3. If a pending item is now done, move it from ❌ to ✅ in `docs/09_STATUS.md`
4. If a new bug is found, add it to the Known Bugs section in `docs/09_STATUS.md`
5. Confirm with: **"✅ docs updated: [list of files changed]"**

**Read order for each session:**
- Always: `docs/00_INDEX.md` + `docs/11_RULES.md`
- Task-specific: 1–2 files per the index routing table
- After changes: `docs/10_CHANGELOG.md` + affected file(s)

---

## What's Mock / What's Real

| Integration | Status |
|-------------|--------|
| Auth | Demo only (plain passwords in SQLite) |
| Email (Gmail) | OAuth scaffold exists; only works if `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` configured |
| Email (SMTP/SendGrid) | Backend compat paths exist; not exposed in normal Settings UI |
| WhatsApp | Mock mode by default; Twilio/Cloud API via `.env` only |
| Telegram | Real — works when `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` set |
| Google Calendar | Placeholder fields only — NOT connected |
| AI (DeepInfra) | Real when `AI_PROVIDER=deepinfra` + valid `DEEPINFRA_API_KEY` |
| AI (OpenAI) | Real when valid `OPENAI_API_KEY` set |
| AI (local) | Always available as fallback |
| Vendor emails | Mock/approval-queue only — never auto-sent |
| Payments | Not implemented |
