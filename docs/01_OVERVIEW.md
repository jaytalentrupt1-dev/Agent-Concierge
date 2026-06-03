# Project Overview — Agent Admin-IT

**Product name:** Agent Concierge
**Goal:** Local AI Admin Agent MVP for automating internal admin workflows while keeping risky actions behind human approval. Main demo: Vendor Review Meeting automation.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Pydantic, SQLite, Uvicorn |
| Frontend | React 18, Vite 6, lucide-react, recharts, plain CSS |
| DB | SQLite — `backend/admin_agent.db` (git-ignored) |
| AI | DeepInfra (DeepSeek-V3) or OpenAI fallback or local mock |
| Scheduler | APScheduler `BackgroundScheduler` (UTC) |
| Tests | pytest (backend), Node ESM scripts (frontend formatters) |

---

## Ports

| Service | URL |
|---------|-----|
| Backend | `http://127.0.0.1:8001` |
| Frontend | `http://127.0.0.1:5173` (or 5174 on relaunch) |

`VITE_API_BASE_URL=http://127.0.0.1:8001` must be set in `frontend/.env`.

---

## Folder Structure (top-level)

```
Agent Admin-IT/
├── backend/
│   ├── app/
│   │   ├── main.py                 ← FastAPI app + ALL routes (5000+ lines)
│   │   ├── core/config.py          ← env loading, settings
│   │   ├── models/schemas.py       ← Pydantic request schemas
│   │   ├── repositories/admin_repository.py  ← SQLite data access
│   │   ├── services/
│   │   │   ├── scheduler.py        ← APScheduler + 4 agents
│   │   │   ├── telegram_service.py ← send_telegram_sync()
│   │   │   ├── action_handler.py   ← Conci AI slot-filling bridge
│   │   │   ├── conversation_state.py ← in-memory slot state
│   │   │   ├── tool_executor.py    ← intent → repo calls
│   │   │   ├── conci_agent.py      ← intent classifier
│   │   │   ├── auth_service.py     ← demo auth, role helpers
│   │   │   ├── audit_service.py    ← audit logging
│   │   │   ├── approval_rules.py   ← centralised approval logic
│   │   │   ├── workflow.py         ← Vendor Review Meeting workflow
│   │   │   └── ...
│   │   └── data/mock_data.py
│   ├── tests/test_vendor_workflow.py
│   ├── requirements.txt
│   └── admin_agent.db              ← runtime, git-ignored
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 ← main React app + all screens
│   │   ├── api.js                  ← all fetch calls, Bearer auth
│   │   ├── main.jsx                ← entrypoint, CSS import order
│   │   ├── styles.css              ← legacy ~9k-line stylesheet
│   │   ├── styles/globals.css      ← override layer (!important wins)
│   │   ├── components/
│   │   │   ├── AgentsDashboard.jsx
│   │   │   ├── KpiCard.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── NotFound.jsx
│   │   │   ├── ServerError.jsx
│   │   │   └── ui/ (CustomSelect, FormError, Skeleton)
│   │   ├── hooks/useFormValidation.js
│   │   ├── authStorage.js
│   │   ├── navigationConfig.js
│   │   └── vendorBilling.js
│   └── package.json
├── docs/                           ← this folder
├── PROJECT_CONTEXT.md              ← pointer to docs/
├── .env.example                    ← safe to commit
└── .env                            ← LOCAL ONLY, never commit
```

---

## How to Run

```bash
# Backend (first time)
cd backend && python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Backend (already set up)
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend && npm install && npm run dev

# Tests
backend/.venv/bin/python -m pytest backend/tests
cd frontend && npm run build
node frontend/src/vendorBilling.test.mjs
```

---

## Key Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_API_BASE_URL` | Frontend API base | `http://127.0.0.1:8001` |
| `AI_PROVIDER` | `deepinfra` or blank | blank (mock) |
| `DEEPINFRA_API_KEY` | DeepInfra key | — |
| `DEEPINFRA_MODEL` | Model name | `deepseek-ai/DeepSeek-V3` |
| `OPENAI_API_KEY` | OpenAI key (optional) | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot | — |
| `TELEGRAM_CHAT_ID` | Telegram chat | — |
| `ADMIN_AGENT_DB` | SQLite path | `backend/admin_agent.db` |
