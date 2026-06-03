# API Endpoints — Agent Admin-IT

**Base URL:** `http://127.0.0.1:8001`
**Auth:** `Authorization: Bearer <token>` header on all protected routes.
All routes defined in `backend/app/main.py` inside the `create_app()` factory.

---

## Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | Public | `{email, password}` → `{token}` |
| POST | `/api/auth/logout` | User | Invalidate session token |
| GET | `/api/auth/me` | User | Returns current user dict |
| GET | `/api/health` | Public | Health check |

---

## Users (Admin only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users` | Admin | List all non-demo users |
| POST | `/api/users` | Admin | Create user |
| PATCH | `/api/users/{user_id}` | Admin | Edit user name/email/role |
| POST | `/api/users/{user_id}/reset-password` | Admin | Reset password |
| DELETE | `/api/users/{user_id}` | Admin | Delete user (cannot delete own) |
| GET | `/api/users/assignable` | User | Users the current user can assign tasks to |

---

## Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard` | User | Role-scoped summary cards, charts, recent data |

---

## Tickets

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/tickets` | User | List tickets (role-scoped) |
| POST | `/api/tickets` | User | Create ticket |
| PUT | `/api/tickets/{ticket_id}` | User | Update ticket |
| PATCH | `/api/tickets/{ticket_id}/status` | Admin/IT | Update status |

---

## Tasks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/tasks` | User | List tasks (role-scoped) |
| POST | `/api/tasks` | User | Create task |
| GET | `/api/tasks/{id}` | User | Get single task |
| PUT | `/api/tasks/{id}` | User | Update task |
| PATCH | `/api/tasks/{id}/status` | User | Update status |
| DELETE | `/api/tasks/{id}` | User | Delete task |

---

## Vendors

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/vendors` | Admin/Finance | List vendors |
| POST | `/api/vendors` | Admin | Create vendor |
| PUT | `/api/vendors/{vendor_id}` | Admin | Update vendor |
| PATCH | `/api/vendors/{vendor_id}/close` | Admin | Close vendor |
| POST | `/api/vendors/{vendor_id}/close` | Admin | Close vendor (compat) |
| PATCH | `/api/vendors/{vendor_id}/reopen` | Admin | Reopen vendor |
| POST | `/api/vendors/{vendor_id}/reopen` | Admin | Reopen vendor (compat) |
| POST | `/api/vendors/{vendor_id}/email` | Admin | Draft vendor email → approval queue |

---

## Expenses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/expenses` | User | List expenses (role-scoped) |
| POST | `/api/expenses` | User | Create expense |
| PUT | `/api/expenses/{expense_id}` | User | Update expense |
| PATCH | `/api/expenses/{expense_id}/status` | Admin/Finance | Update status |
| POST | `/api/expenses/import/preview` | Admin/Finance | Preview CSV/XLSX import |
| POST | `/api/expenses/import/confirm` | Admin/Finance | Confirm and persist import |

---

## Inventory

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/inventory` | Admin/IT/Finance | List items |
| POST | `/api/inventory` | Admin/IT | Create item |
| PUT | `/api/inventory/{item_id}` | Admin/IT | Update item |
| DELETE | `/api/inventory/{item_id}` | Admin/IT | Delete item |
| PATCH | `/api/inventory/{item_id}/status` | Admin/IT | Update status |
| POST | `/api/inventory/bulk-delete` | Admin/IT | Bulk delete by ID list |
| POST | `/api/inventory/import/preview` | Admin/IT | Preview CSV/XLSX |
| POST | `/api/inventory/imports` | Admin/IT | Confirm import → creates batch |
| GET | `/api/inventory/imports` | Admin/IT | List import batches |
| GET | `/api/inventory/imports/{id}/items` | Admin/IT | Items in a batch |
| DELETE | `/api/inventory/imports/{id}` | Admin/IT | Delete batch + its items |

---

## Travel & Calendar

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/travel` | Admin/Finance | List travel records |
| POST | `/api/travel` | Admin/Finance | Create travel record |
| PUT | `/api/travel/{travel_id}` | Admin/Finance | Update travel record |
| GET | `/api/travel/summary` | Admin/Finance | Analytics summary |
| GET | `/api/calendar-events` | Admin/Finance | List calendar events |
| POST | `/api/calendar-events` | Admin/Finance | Create event |
| PUT | `/api/calendar-events/{event_id}` | Admin/Finance | Update event |

---

## Reports

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reports` | Admin/IT/Finance | List reports |
| POST | `/api/reports/import` | Admin/IT/Finance | Import report file |
| GET | `/api/reports/{id}/download` | Admin/IT/Finance | Download file |
| GET | `/api/reports/{id}/preview` | Admin/IT/Finance | Extracted text/rows for in-app preview |
| GET | `/api/reports/{id}/preview-file` | Admin/IT/Finance | Raw file bytes (PDF blob) |
| GET | `/api/reports/export` | Admin/IT/Finance | Filtered CSV export |
| DELETE | `/api/reports/{id}` | Admin/IT/Finance | Delete report |

---

## Approvals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/approvals` | User | List approvals (role-scoped) |
| PATCH | `/api/approvals/{approval_id}` | User | Approve/reject |

---

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notifications` | User | List notifications (role-scoped) |
| PATCH | `/api/notifications/{id}/read` | User | Mark one read |
| PATCH | `/api/notifications/read-all` | User | Mark all read |

---

## Agents (Admin only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/agents/status` | Admin | List 4 agents with paused/running state |
| GET | `/api/agents/logs` | Admin | Query agent_logs (`?agent_name=&limit=`) |
| POST | `/api/agents/run/{agent_name}` | Admin | Immediately run one agent |
| PATCH | `/api/agents/{agent_name}/toggle` | Admin | Pause / resume APScheduler job |

---

## Telegram

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/telegram/test` | Admin | Send test Telegram message |

---

## Connectors & Communications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/connectors` | User | List user's connectors |
| POST | `/api/connectors/email/configure` | User | Configure email connector |
| GET | `/api/connectors/google/start` | User | Start Google OAuth flow |
| GET | `/api/connectors/google/callback` | Public | Google OAuth callback |
| POST | `/api/connectors/google/disconnect` | User | Disconnect Gmail |
| POST | `/api/connectors/google/test-email` | User | Test Gmail send |
| POST | `/api/connectors/whatsapp/configure` | User | Configure WhatsApp |
| POST | `/api/connectors/email/test` | User | Test email send |
| POST | `/api/connectors/whatsapp/test` | User | Test WhatsApp send |
| POST | `/api/connectors/disconnect` | User | Disconnect any connector |
| GET | `/api/communications/logs` | User | Communication log |
| POST | `/api/communications/send-email` | User | Send email |
| POST | `/api/communications/send-whatsapp` | User | Send WhatsApp |
| POST | `/api/communications/send-both` | User | Send both |

---

## Conci AI Chat

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/chat/assistant` | User | Main chat endpoint (JSON or multipart with file) |
| POST | `/api/chatbot/ask` | User | Legacy alias for `/api/chat/assistant` |
| POST | `/api/chat/command` | User | Vendor Review Meeting workflow trigger |
| POST | `/api/agent/plan` | User | AI planning endpoint |
| POST | `/api/requests/route` | User | Request routing + approval rules |

---

## Audit & Dev

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/audit-log` | User | Role-scoped audit log |
| POST | `/api/dev/reset` | Admin | Reset demo data |
