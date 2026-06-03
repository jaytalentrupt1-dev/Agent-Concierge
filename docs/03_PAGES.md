# Pages & Modules — Agent Admin-IT

All pages are rendered inside `frontend/src/App.jsx`. Route state is managed via `window.history` (no React Router).

---

## Navigation Routes

| Path | Page | Roles | Component / Section |
|------|------|-------|---------------------|
| `/dashboard` | Dashboard | All | `DashboardPage` in App.jsx |
| `/vendors` | Vendors | admin, finance_manager | inline in App.jsx |
| `/tasks` | Tasks | All | inline in App.jsx |
| `/tickets` | Tickets | All | inline in App.jsx |
| `/approvals` | → redirects to `/tickets` | — | compat alias |
| `/travel` | Travel & Calendar | admin, finance_manager | inline in App.jsx |
| `/expenses` | Expenses | admin, finance_manager, it_manager (partial) | inline in App.jsx |
| `/inventory` | Inventory | admin, it_manager, finance_manager (read) | inline in App.jsx |
| `/reports` | Reports | admin, it_manager, finance_manager | inline in App.jsx |
| `/agents` | Agents Dashboard | admin only | `AgentsDashboard.jsx` component |
| `/settings` | Settings | All | inline in App.jsx |

---

## Page Details

### Dashboard (`/dashboard`)
- Role-specific command centre via `GET /api/dashboard`
- **Admin:** 6 summary cards, 4 charts (Tickets/Tasks/Expenses/Inventory), Recent Tickets, Pending Approvals, Recent Activity, Vendor Billing Dashboard in compact modal cards
- **IT Manager:** 6 IT summary cards, 3 IT charts, Recent IT Tickets, Inventory Status, IT Tasks
- **Finance Manager:** 6 finance cards, 4 finance charts, Expense Exceptions, Pending Finance Approvals, Recent Travel
- **Employee:** 4 personal cards, My Recent Tickets, My Tasks, My Requests
- Conci AI chat panel (right column, ~35% width, sticky). Persists in `sessionStorage`.

### Vendors (`/vendors`)
- Admin: full CRUD (add/edit/close/reopen/send email to approval queue)
- Finance: read-only
- Filters: Status, Service, Billing cycle, Branch
- Pagination: 10/page

### Tasks (`/tasks`)
- All roles (scoped by role backend-side)
- Summary cards: Total, Open, In Progress, Overdue, Completed
- Actions: View, Edit, Change Status, Delete
- Assigned To dropdown backed by `GET /api/users/assignable`
- Categories: Admin, IT, Finance, Vendor, Inventory, Travel, Expense, Report, Other
- Statuses: Open, In Progress, Waiting Approval, Completed, Cancelled

### Tickets (`/tickets`)
- All roles (scoped by role backend-side)
- Unified IT + Admin ticket directory
- Filters: Type (IT/Admin), Status, Priority, Branch
- Employee: create + view own only; IT Manager: IT tickets; Finance: finance Admin tickets; Admin: all
- Statuses: Open, In Progress, Waiting Approval, Resolved, Closed, Overdue

### Travel & Calendar (`/travel`)
- Admin + Finance Manager only
- Travel records table + Calendar events table
- Smart dashboard cards (spend, upcoming trips, pending approvals, over-budget, today's events)
- Analytics summary tables
- Google Calendar fields present but NOT connected (placeholder only)

### Expenses (`/expenses`)
- Admin + Finance Manager (full); IT Manager (limited view)
- CSV/XLSX import with preview before confirm
- Categories: Travel, Food, Hotel, Local Conveyance, Office Supplies, Software, Internet/Phone, Vendor Payment, Client Meeting, Training, Miscellaneous

### Inventory (`/inventory`)
- Admin + IT Manager: full management; Finance: read-only
- Features: add/edit, CSV/XLSX import, bulk delete, status update, import batch history
- Row selection: current page / 50 / 100 / all filtered rows
- Import template download: `inventory_import_template.csv`

### Reports (`/reports`)
- Admin: all reports; IT Manager: IT reports; Finance: Finance reports; Employee: blocked
- File types: CSV, XLSX, PDF, TXT, MD, DOCX, DOC
- Files stored locally under `uploads/reports/`
- Preview modal: CSV/XLSX show table rows; PDF embeds; TXT/MD/DOCX show text

### Agents (`/agents`) — Admin only
- Component: `frontend/src/components/AgentsDashboard.jsx`
- Shows 4 agent cards with: status (Running/Paused), last/next run, toggle switch, Run Now, View Logs
- Toggle calls `PATCH /api/agents/{name}/toggle`
- Logs modal shows `agent_logs` table entries
- Test Telegram button calls `POST /api/telegram/test`

### Settings (`/settings`)
- **All roles:** Profile Settings + Connectors (Email/WhatsApp)
- **Admin only:** User Management tab
- Connectors: Gmail OAuth (requires `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`) or mock mode
- WhatsApp: Twilio / Cloud API / mock mode
- User Management: create/edit/delete users (excludes demo users from table)

---

## Multi-Branch Support

Branches: **Pune · Ahmedabad · Vadodara · Noida**

Supported in: Vendors, Inventory, Tickets, Expenses, Travel & Calendar.
All add/edit forms include branch dropdown. All list endpoints accept `?branch=` filter.
Old rows default to Pune. Conci AI understands branch-specific questions.
