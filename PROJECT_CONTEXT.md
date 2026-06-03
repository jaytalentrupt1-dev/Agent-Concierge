# Agent Admin-IT — Project Context

This project uses a split-doc system. **Do not read this file for task context.**

---

## → Start Here: [`docs/00_INDEX.md`](docs/00_INDEX.md)

The index tells you exactly which 1–2 files to read for any given task.
Reading the full set takes ~5 minutes. Reading the right 2 files takes ~30 seconds.

---

## Maintenance Rule

After completing **any** task that touches code:

1. Update the relevant file(s) in `docs/`
2. Add a new entry at the top of `docs/10_CHANGELOG.md`
3. Move completed items from ❌ to ✅ in `docs/09_STATUS.md`
4. Confirm with: **"✅ docs updated: [list of files]"**

Never rewrite unaffected doc sections. Never update only PROJECT_CONTEXT.md — update the `docs/` files instead.

---

## Quick Facts (no doc read needed)

| Item | Value |
|------|-------|
| Backend | FastAPI · port **8001** · `backend/app/main.py` |
| Frontend | React/Vite · port **5173** · `frontend/src/` |
| Database | SQLite · `backend/admin_agent.db` |
| Auth | Bearer token · `sessionStorage["admin_agent_token"]` |
| Red accent | `#EF4444` |
| Never touch | `.env` |
| Docs folder | `docs/` (12 files, see index) |
