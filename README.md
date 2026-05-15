# AI Admin Agent MVP

For future Codex sessions, read `PROJECT_CONTEXT.md` first.
For any new Codex account/session, read `PROJECT_CONTEXT.md` first.

Local FastAPI + React MVP for an AI admin agent. The first complete workflow is Vendor Review Meeting automation:

1. Schedule tomorrow's vendor review meeting from mock calendars and people.
2. Prepare an agenda and attach mock files.
3. Generate an internal reminder.
4. Generate meeting notes from a mock transcript.
5. Extract decisions and action items.
6. Draft a vendor follow-up email.
7. Queue the email for human approval because it is external communication.
8. Let a reviewer approve/send, edit, or cancel.
9. Create and store an AI Admin Agent plan that classifies the request and decides the automation level.
10. Update the dashboard and audit log.

## Stack

- Backend: Python FastAPI
- Frontend: React + Vite
- Database: SQLite
- AI layer: deterministic local/mock Conci AI fallback, optional DeepInfra chat completions for Conci AI, and OpenAI Responses API planning support
- Safety: policy service gates external vendor communication and other risky actions

OpenAI's docs recommend the Agents SDK when an app needs code-first orchestration, tools, handoffs, guardrails, tracing, or sandbox execution:
https://developers.openai.com/api/docs/libraries#install-the-agents-sdk

## Project Structure

```text
backend/
  app/
    core/config.py
    data/mock_data.py
    db/database.py
    main.py
    models/schemas.py
    repositories/admin_repository.py
    services/
      agent_planner.py
      approval_service.py
      audit_service.py
      mock_ai.py
      policy.py
      workflow.py
  tests/test_vendor_workflow.py
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    main.jsx
    styles.css
  index.html
  package.json
  vite.config.js
```

## Run Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API will be at `http://127.0.0.1:8000`.

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The web app will be at `http://127.0.0.1:5173`.

## Run Tests

```bash
python3 -m pytest backend/tests
```

The tests exercise the vendor workflow, approval queue, and audit log.

## Demo Authentication

This is demo authentication only. For production, replace with Google/Microsoft SSO, hashed passwords, secure sessions, RBAC, and audit-grade logging.

Demo users are seeded automatically:

```text
admin@company.com / admin123 / admin / Admin User
it@company.com / it123 / it_manager / IT Manager
finance@company.com / finance123 / finance_manager / Finance Manager
employee@company.com / employee123 / employee / Employee User
```

Users must log in before accessing the dashboard, command screen, approval queue, or audit log. Admin users can manage users and roles from the User Management page. Approval permissions are role based: admins can approve all requests; Finance Manager/Admin can approve expense, payment, invoice, and reimbursement approvals; IT Manager/Admin can approve IT support, account, device, and password workflow approvals; employees cannot approve sensitive actions.

## AI Agent Modes

## Local Environment

Create local environment settings from the committed example file:

```bash
cp .env.example .env
```

To use DeepInfra credits for Conci AI, put your real DeepInfra key in `.env` and set `AI_PROVIDER=deepinfra`:

```text
AI_PROVIDER=deepinfra
DEEPINFRA_API_KEY=your-real-deepinfra-key
DEEPINFRA_MODEL=deepseek-ai/DeepSeek-V3
```

Never commit `.env`; it is ignored by git so real API keys stay local. `.env.example` is safe to commit because it contains no secret values.

If `AI_PROVIDER` is not `deepinfra`, `DEEPINFRA_API_KEY` is missing, the key is a placeholder, or DeepInfra returns an error, Conci AI falls back to the existing local/mock intent and response behavior.

You can test DeepInfra without starting the app:

```bash
export DEEPINFRA_API_KEY="your-real-deepinfra-key"
python3 test_deepinfra.py
```

To use OpenAI for the legacy planner layer, put your real OpenAI API key in `.env`:

```text
OPENAI_API_KEY=your-real-api-key
OPENAI_MODEL=gpt-5.5
```

If `OPENAI_API_KEY` is missing or left as the placeholder value, the planning layer falls back to mock AI behavior.

### Mock AI mode

By default, the app can run with deterministic mock behavior. Leave `DEEPINFRA_API_KEY` and `OPENAI_API_KEY` unset:

```bash
unset DEEPINFRA_API_KEY
unset OPENAI_API_KEY
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In mock mode, the AI Admin Agent still returns a structured plan, but it is created locally with deterministic rules.

### DeepInfra Conci AI mode

Set `AI_PROVIDER=deepinfra` and `DEEPINFRA_API_KEY` to let Conci AI use DeepInfra's OpenAI-compatible chat completions endpoint for intent classification and answer refinement:

```bash
cp .env.example .env
# edit .env:
# AI_PROVIDER=deepinfra
# DEEPINFRA_API_KEY="your-deepinfra-api-key"
# DEEPINFRA_MODEL=deepseek-ai/DeepSeek-V3
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Conci AI still applies backend role filters before creating an answer. When DeepInfra is configured, the backend asks DeepInfra to classify the user's full sentence first, including a small previous-topic hint for follow-up clarifications such as `I mean earlier history`, `show more`, `give all`, or `only food`. Only after that classification does the backend route the request to role-filtered app data. The backend keeps local intent priority guards for overlapping phrases, so requests like `show calendar events` are not mistaken for date questions even if an external classifier returns a weaker intent. DeepInfra receives only the user's message/topic hint for intent classification and only the already role-filtered answer/bullets for response cleanup. If DeepInfra is unavailable or the key is missing, Conci AI falls back to the current local/mock behavior.

Conci AI has a local intent-understanding fallback for demo mode. It normalizes messages, fixes common typos, uses recent chat topic context for follow-up clarifications, and supports natural-language requests such as `sho me recent tickets`, `show my ticket history`, `I mean earlier history`, `show more`, `show calender events`, `status of my vendor issue ticket`, `show food vendors`, `give me food vendor deatils`, `how many vendors do we have`, `what todays date`, `create tikcet for laptop issue`, pending approvals, vendor billing/details, inventory status/update questions, monthly or category-wise expenses, recent travel records, calendar events, and imported reports. The backend always filters tickets, tasks, vendors, inventory, expenses, travel/calendar, reports, approvals, and settings data by the logged-in user's role before an answer is built or any text is sent to DeepInfra.

### OpenAI planner mode

Copy `.env.example` to `.env`, then set `OPENAI_API_KEY` to use the OpenAI Responses API for the agent planning layer:

```bash
cp .env.example .env
# edit .env:
# OPENAI_API_KEY="your-api-key"
# OPENAI_MODEL="gpt-5.5"
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend loads environment variables from the repo-root `.env` file and from `backend/.env` if present. The model is configurable with `OPENAI_MODEL` and defaults to `gpt-5.5`. If `OPENAI_API_KEY` is missing, the planner falls back to mock mode. If the OpenAI SDK or API call is unavailable, the planner also falls back to mock planning.

The existing transcript summary adapter remains mock-first. To experiment with OpenAI-generated transcript summaries too:

```bash
export USE_OPENAI_AI=true
```

### Environment variables

```text
OPENAI_API_KEY       Optional. Enables OpenAI Responses API agent planning when set.
OPENAI_MODEL         Optional. Defaults to gpt-5.5.
USE_OPENAI_AI        Optional. Defaults to false. Enables the OpenAI transcript summary adapter.
AI_PROVIDER          Optional. Set to deepinfra to enable DeepInfra for Conci AI.
DEEPINFRA_API_KEY    Optional. Enables DeepInfra Conci AI mode when AI_PROVIDER=deepinfra and the key is non-placeholder.
DEEPINFRA_MODEL      Optional. Defaults to deepseek-ai/DeepSeek-V3.
ADMIN_AGENT_DB       Optional. SQLite database path. Defaults to backend/admin_agent.db.
```

## AI Admin Agent Plan

Every command first goes through the AI Admin Agent planning layer. The plan includes:

- `task_type`
- `automation_level`
- `summary`
- `steps`
- `required_tools`
- `approval_required`
- `approval_reason`
- `risk_level`
- `expected_outputs`

Plans are stored in the `agent_plans` table and summarized in the audit log as `agent.plan.created`. The dashboard shows the latest classification and automation level.

## Safety Rules Captured

The AI can automatically create calendar holds, prepare agendas, generate reminders, create notes, create tasks, and update the dashboard.

Human approval is required before external vendor emails, payments, travel bookings, expense approvals, contract changes, confidential document sharing, file deletion, legal/compliance decisions, emergency/safety decisions, and policy exceptions.

File deletion never runs automatically. Legal/compliance decisions, emergency/safety decisions, policy exceptions, and unknown high-risk requests become `human_decision_required`.

Every AI or human action is written to `audit_logs` with timestamp, action, status, and approval reason when relevant.
