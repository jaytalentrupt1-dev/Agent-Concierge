# Docs Index — Agent Admin-IT

**Read this file first on every session. Then read only the 1–2 files relevant to your task.**
Always read `11_RULES.md` before writing code. Always update `10_CHANGELOG.md` after changes.

---

## Task → Files to Read

| Task type | Read these |
|-----------|-----------|
| Adding / changing an API endpoint | `06_API_ENDPOINTS.md` + `11_RULES.md` |
| Fixing an agent / scheduler bug | `04_AGENTS.md` + `09_STATUS.md` |
| Adding a new page or frontend component | `03_PAGES.md` + `08_FRONTEND.md` |
| Auth, roles, or permissions bug | `02_ROLES.md` + `06_API_ENDPOINTS.md` |
| Database schema change | `05_DATABASE.md` + `11_RULES.md` |
| Telegram / notification work | `07_TELEGRAM.md` + `04_AGENTS.md` |
| Fixing a known bug | `09_STATUS.md` + relevant domain doc |
| UI / theme / CSS change | `08_FRONTEND.md` + `11_RULES.md` |
| Understanding project from scratch | `01_OVERVIEW.md` → all files in order |
| Post-task update | `10_CHANGELOG.md` + affected file(s) |

---

## File Map

| File | Contents | ~Lines |
|------|----------|--------|
| `00_INDEX.md` | **This file** — routing map | 50 |
| `01_OVERVIEW.md` | Stack, ports, folder structure, run commands | 80 |
| `02_ROLES.md` | User roles, permissions, demo credentials | 70 |
| `03_PAGES.md` | All pages/modules, routes, status | 120 |
| `04_AGENTS.md` | 4 background agents, scheduler, toggle API | 90 |
| `05_DATABASE.md` | All SQLite tables and key columns | 110 |
| `06_API_ENDPOINTS.md` | All API routes grouped by category | 130 |
| `07_TELEGRAM.md` | Bot env vars, send function, triggers | 40 |
| `08_FRONTEND.md` | Components, CSS architecture, theme, UI conventions | 100 |
| `09_STATUS.md` | Done ✅ / Pending ❌ / Known bugs | 60 |
| `10_CHANGELOG.md` | Change log, newest first | growing |
| `11_RULES.md` | Strict rules — never break these | 50 |

---

## Quick Facts (no file read needed)

- **Backend:** FastAPI on port **8001** — `backend/app/main.py`
- **Frontend:** React/Vite on port **5173** — `frontend/src/`
- **DB:** SQLite at `backend/admin_agent.db`
- **Auth pattern:** `Authorization: Bearer <token>` header
- **Admin guard:** `Depends(admin_user)` or `if user.get("role") != "admin": raise 403`
- **Theme:** `#0A0A0A` bg · `#EF4444` red accent · `#141414` cards
- **CSS override file:** `frontend/src/styles/globals.css` (wins via `!important`)
- **Never touch:** `.env` file
