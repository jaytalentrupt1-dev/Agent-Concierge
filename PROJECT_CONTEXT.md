# AI Admin Agent Project Context

This file is the source-of-truth handoff note for future Codex sessions. It is based only on repository files and the product direction documented in `README.md`.

## Latest Session Snapshot

Last updated during the current Codex session on 2026-05-11 after adding role-scoped task assignment users and task assignment notifications.

Product goal:

- Agent Concierge is a local AI Admin Agent MVP for automating internal administrative work while keeping risky actions behind human approval.
- The main demo workflow is Vendor Review Meeting automation.
- All external systems are mocked. Do not connect real Gmail, Calendar, Slack, Teams, Jira, ServiceNow, payment, travel, or vendor APIs until explicitly requested.

Current stack:

- Backend: Python, FastAPI, Pydantic, SQLite, Uvicorn, OpenAI Python SDK dependency, `python-dotenv`.
- Frontend: React, Vite, `lucide-react`, `recharts`, plain CSS.
- Testing: `pytest` for backend tests; small Node-based frontend tests for vendor billing formatting and navigation access.
- Runtime DB: SQLite at `backend/admin_agent.db` by default. Runtime DB files are ignored by git.

Current implemented features:

- Demo authentication with local SQLite users and bearer-token sessions.
- Role-based navigation and approval permissions for normalized roles `admin`, `it_manager`, `finance_manager`, and `employee`.
- AI planning endpoint with OpenAI planner mode and deterministic mock fallback.
- Request routing endpoint backed by centralized approval rules.
- Vendor Review Meeting workflow through `POST /api/chat/command`.
- Dashboard, Tasks, Tickets, Vendors, Travel & Calendar, Expenses, Inventory, Reports, and Settings screens. The standalone Meetings page has been removed from app navigation/routing; the Vendor Review Meeting automation workflow remains available through the dashboard command workflow.
- Dashboard is a role-based command center with theme-aware light/dark styling. Admin, IT Manager, Finance Manager, and Employee receive backend-filtered summary cards, allowed quick actions, role-specific recent-work sections, and empty states when data is missing; Admin/IT/Finance also receive Recharts chart cards while Employee receives no chart payload. Admin/Finance also see full vendor billing dashboard data; IT Manager sees vendor service summary without billing amounts; Employee sees no vendor billing dashboard. The Admin Dashboard keeps summary cards/charts visible but moves Recent Tickets, Pending Approvals, Recent Activity, and Vendor Billing Dashboard into compact action cards that open readable detail modals. The IT Manager Dashboard uses an `IT Command Center` composition with IT summary cards, IT quick actions, a three-card chart row on desktop, Recent IT Tickets, Inventory Status, IT Tasks, and the same compact bottom cards using role-scoped IT data. The Finance Manager Dashboard uses a `Finance Command Center` composition with finance summary cards, a reduced-height two-by-two chart grid, Expense Exceptions, Pending Finance Approvals, Recent Travel Records, and bottom compact cards for Recent Tickets, Pending Approvals, Recent Activity, and Vendor Billing Dashboard that open finance-scoped detail modals. The Employee Dashboard uses a personal `My Command Center` composition with four personal summary cards, Create Ticket/Create Task Request quick actions, My Recent Tickets, My Tasks, My Requests, and compact bottom cards for Recent Tickets, Pending Approvals, Recent Activity, and My Pending Requests; all are scoped to the logged-in employee's visible tickets/tasks/requests/activity. The Dashboard uses a two-column layout with the main command center on the left and a fixed/sticky right-side `Conci AI` chat panel. Dashboard-specific CSS now uses theme variables so light mode uses light backgrounds/cards/dark text while dark mode keeps the previous navy command-center look. `Conci AI` calls `POST /api/chat/assistant`, answers only from the current user's role-scoped backend data, preserves chat history/draft text in `sessionStorage`, supports editable multiline input, can send attached files for temporary backend parsing, and can render compact table responses inside chat bubbles when the backend returns tabular data. Vendor detail table responses resolve contact/phone across `contact_person`, `contactPerson`, `contact`, `phone`, `contact_details`, `contactDetails`, `contact_number`, and `contactNumber`, and include service, billing, end date, and status where the user's role is allowed to see them.
- Tasks module with role-scoped task list, create/edit/view/status/delete actions, real user assignment fields, search/filter controls, summary cards, backend APIs, assignment notifications, and audit logs. Existing Vendor Review Meeting action items continue to use the same extended `tasks` table.
- Human Ticket Queue with approve, edit, cancel, role gating, and audit logging.
- Ticket Directory for unified IT/Admin tickets with search, Type/Status/Priority filters, create/edit/status actions, and role-scoped backend access.
- Ticket notifications for created/resolved/closed/status-changed ticket events, with role-scoped visibility and per-user read state.
- Admin User Management in Settings.
- Vendor Directory with add/edit/close/reopen/send email, billing amount + cycle, office address, optional end date, local search/filter controls, role gating, and audit logs.
- Expenses module with all-expenses table, add/edit expense form, Admin/Finance-only CSV and `.xlsx` import, preview validation before saving, role-scoped backend access, and audit logs. The visible Expenses page no longer shows the generic `Expenses / Welcome back` page heading, summary cards, Basic Reports, Approval Queue, or Policy Exceptions UI/table column.
- Travel & Calendar module with smart travel dashboard cards, travel records table, calendar events table, add/edit modals, search/filter controls, analytics summary tables, role-scoped backend access, audit logs, and Google Calendar placeholder fields only.
- Inventory List with add/edit item forms, local search/filter controls, CSV/`.xlsx` import validation, import preview before save, and role-gated backend persistence.
- Reports module with role-scoped report list, CSV/XLSX/PDF import, local upload storage, per-report download/export, filtered CSV export, delete action, search/filter controls, and audit logs.
- Settings > Connectors for every logged-in role with per-user Email and WhatsApp connector cards, provider configuration, test connection, send test message, disconnect actions, and communication log tracking.
- Shared communication send flow for Vendors, Tickets, Expenses, Reports, and Settings test messages. Senders choose Email, WhatsApp, or Both, preview the message, then confirm before the backend writes communication logs.
- Vendor billing normalization is centralized in the frontend billing helper so add/edit save verification and directory display use the same amount/cycle normalization.
- Email/WhatsApp connectors default to mock mode when credentials are missing. SMTP, SendGrid, Twilio WhatsApp, and WhatsApp Cloud API service paths exist behind `.env` configuration only; no real credentials are committed. Other external systems remain mocked.

Current UI/navigation status:

- Visible product name is `Agent Concierge`.
- Top-left logo initials are `AC`.
- Desktop left sidebar has been removed.
- The top app header follows the Agent Concierge reference UI:
  - left AC square logo and `Agent Concierge` brand
  - center global search input with search icon, `Search anything...` placeholder, and `⌘ K` hint
  - notification bell with red badge, sun/moon theme toggle, divider, and user profile dropdown on the right
- Main app navigation is a rounded horizontal section container under the top utility bar and is filtered per logged-in role.
- Admin navigation shows Dashboard, Vendors, Tasks, Tickets, Travel & Calendar, Expenses, Inventory, Reports, and Settings.
- IT Manager navigation shows Dashboard, Inventory, Tasks, Tickets, Reports, and Settings.
- Finance Manager navigation shows Dashboard, Travel & Calendar, Expenses, Reports, Tasks, Tickets, Vendors, Inventory, and Settings.
- Employee navigation shows Dashboard, Tickets, Settings, and Tasks.
- Top navigation uses existing URL routing and active-page highlighting.
- Supported paths are `/dashboard`, `/tasks`, `/tickets`, `/vendors`, `/travel`, `/expenses`, `/inventory`, `/reports`, and `/settings`. Legacy `/approvals` still maps to the Tickets section for refresh/backward compatibility. `/meetings` is no longer mapped and is redirected back to Dashboard by the frontend route restore flow.
- Browser refresh restores the current page from the URL.
- Session tokens are stored only in `sessionStorage` as `admin_agent_token` and restored before protected route rendering; legacy `localStorage` auth tokens are cleared on load/write.
- Unauthenticated app routes render only the login screen, with no app shell/header/nav. Deep links such as `/vendors`, `/inventory`, or `/tickets` stay in the URL while login is shown; after successful login, the app routes back to that requested tab when the user role can access it, otherwise Dashboard.
- Auth restore only clears the token when `/api/auth/me` or a data refresh returns an auth failure, not when a non-auth optional data endpoint fails.
- Top utility actions use the visual reference shell; Mock/OpenAI runtime mode remains visible in Settings.
- Light mode is default.
- Dark mode is supported via the sun/moon toggle and stored in `localStorage` as `admin_agent_theme`.
- The temporary simple neutral global theme was reverted. The UI uses the previous Agent Concierge visual style with purple/blue accents, gradients, status badges/pills, existing button styles, existing table header styling, and the earlier light/dark mode contrast behavior.

Current login/auth status:

- Login page is a compact premium split-screen SaaS login UI.
- Login fields are controlled React state and empty by default.
- Demo credentials are not shown on the login page.
- Password show/hide works.
- Forgot password displays: `Please contact your administrator to reset your password.`
- Google sign-in button displays: `Google sign-in is not connected in demo mode.`
- Tokens are stored only in `sessionStorage` as `admin_agent_token`; this preserves refresh in the same tab but prevents a stale browser-wide localStorage token from opening shared links directly into the app.
- Demo auth only. Production must replace this with SSO, hashed passwords, secure sessions, proper RBAC, and audit-grade logging.

Current role/access model:

- `admin`: Dashboard, Vendors, Tasks, Tickets, Travel & Calendar, Expenses, Inventory, Reports, and Settings; can manage users, roles, vendors, inventory, all tasks, all tickets, all approvals, all reports, and demo reset.
- `it_manager`: Dashboard, Inventory, Tasks, Tickets, Reports, and Settings; can view/manage IT tasks, IT tickets, inventory items/imports, import/export/delete IT reports, and approve IT approvals; cannot see finance-only approvals, tickets, tasks, or reports.
- `finance_manager`: Dashboard, Travel & Calendar, Reports, Tasks, Tickets, Vendors, Inventory, and Settings; can view/manage Finance-related tasks, view/manage finance-related Admin tickets, import/export/delete Finance reports, manage their own Email/WhatsApp connectors, and approve expense, payment, invoice mismatch, and reimbursement approvals; can view Vendors/Inventory read-only and cannot manage vendors/inventory or see IT-only details.
- `employee`: Dashboard, Tickets, Settings/account, and Tasks; can create task requests and IT/Admin tickets, view own/assigned tasks and own tickets, and cannot approve sensitive actions or manage users.

Current demo users and credentials:

```text
admin@company.com / admin123 / admin / Admin User
it@company.com / it123 / it_manager / IT Manager
finance@company.com / finance123 / finance_manager / Finance Manager
employee@company.com / employee123 / employee / Employee User
```

Current User Account/User Management status:

- Non-admin Settings shows Profile Settings and per-user Connectors only.
- Only Admin can open User Management and create/edit/delete accounts.
- Admin Settings uses a Users page header with title `Users`, subtitle `View and manage all created user accounts.`, local `Search users...` input, Filter button, and purple `Add User` button styled like the Vendors `Add Vendor` button.
- User search filters by name, email, raw role, and role label.
- User filters include Role (`All`, `Admin`, `IT Manager`, `Finance Manager`, `Employee`).
- Built-in demo users are marked as demo data and are hidden from the Settings Users table. The table and `X Users` badge show only users actually created by Admin.
- The Users table is a rounded white card with a soft purple table header, thin row dividers, compact inputs, and pagination footer.
- User table columns are User, Name, Email, Role, and Actions.
- The User column shows a colored initials avatar, bold email, and a created-date line like `Created on May 6, 2024 at 3:53 PM`.
- `Add User` opens the existing create modal form with Name, Email, Password, Confirm password, and Role fields.
- The create modal validates required fields, valid email, password length, matching confirmation, and role selection before calling `POST /api/users`.
- Admin can edit user name, email, and role inline, then click `Edit` to save.
- The UI displays friendly role labels (`Admin`, `IT Manager`, `Finance Manager`, `Employee`) while create/edit API calls normalize roles to backend values (`admin`, `it_manager`, `finance_manager`, `employee`) before saving.
- The backend also normalizes legacy/display role labels on user create/edit so older rows or UI state cannot trigger role literal validation errors.
- The red trash action now opens a delete confirmation popup with `Delete` and `Cancel`. Confirming deletes the user from the backend and refreshes the list.
- Admin cannot delete their own currently logged-in account.
- The row more-menu opens the existing mock password reset action.
- User Management role dropdown labels are Admin, IT Manager, Finance Manager, and Employee.
- Backend user endpoints also enforce Admin-only access.
- Legacy demo `operation@company.com` is disabled during demo seeding and is not part of the supported login set.

Current Settings connector status:

- Settings is available in navigation for Admin, IT Manager, Finance Manager, and Employee.
- Admin Settings shows Profile Settings, Connectors, and User Management.
- IT Manager, Finance Manager, and Employee Settings show Profile Settings and Connectors only; User Management remains hidden and backend-protected for non-admin roles.
- Connector cards are available for Email and WhatsApp for every logged-in user with status (`Connected`, `Not Connected`, or `Mock Mode`), provider name, last tested date, Connect / Configure, Test Connection, Disconnect, and Send Test Message actions.
- Email connector providers are SMTP, SendGrid, and Mock Email.
- WhatsApp connector providers are Twilio WhatsApp, WhatsApp Cloud API, and Mock WhatsApp.
- Connector configuration is stored per user in SQLite using `(user_id, connector_type)`, so users can configure only their own Email and WhatsApp connectors. Existing legacy global connector rows are migrated to the Admin user on startup.
- Connector configuration stores only non-secret display metadata in SQLite. Real secrets are expected from `.env`/environment variables; the UI masks secret fields and the backend stores only boolean `has_*` flags for submitted secret values.
- Backend connector endpoints are `GET /api/connectors`, `POST /api/connectors/email/configure`, `POST /api/connectors/whatsapp/configure`, `POST /api/connectors/email/test`, `POST /api/connectors/whatsapp/test`, `POST /api/connectors/disconnect`, and `GET /api/communications/logs`.
- Connector endpoints identify the logged-in user from the bearer token and return/update only that user's connector rows. Admin does not expose other users' connector secrets through these endpoints.
- Message send endpoints are `POST /api/communications/send-email`, `POST /api/communications/send-whatsapp`, and `POST /api/communications/send-both`.
- Communication logs are stored in SQLite with channel, recipient name/email/phone, subject, message, provider, status, related module/record ID, sender identity, sent timestamp, error message, and metadata.
- Basic message templates are seeded for vendor billing reminder, vendor follow-up, expense approval/rejection, missing receipt reminder, ticket created/resolved, report shared, travel approval, and general message.
- Role-gated send access is enforced in the backend. Admin can send all supported communication types; Finance Manager can send finance/vendor billing/expense/report/travel messages; IT Manager can send IT ticket/inventory/task/report messages; Employee is limited to ticket/task/request/general contexts. All roles can send their own Settings connector test messages.
- When sending, the backend uses the current user's connector provider/configuration for that channel. When credentials are missing or provider is set to mock, sends do not fail. They are logged as `mock_sent` and the UI reports `Mock message sent`.
- The shared send modal is currently wired from Vendor Send, Ticket View > Send Update, Expense Edit > Send Update, Report Details > Send Report, and Settings connector Send Test Message. It supports Email, WhatsApp, and Both channels with preview-before-confirm behavior.

Current Tasks feature status:

- Tasks is an implemented internal module at `/tasks`, not just the old dashboard task tracker.
- The existing workflow `tasks` table has been extended in place so Vendor Review Meeting action items and manually created tasks share one storage model.
- Task backend endpoints are `GET /api/tasks`, `POST /api/tasks`, `GET /api/tasks/{id}`, `PUT /api/tasks/{id}`, `PATCH /api/tasks/{id}/status`, and `DELETE /api/tasks/{id}`.
- Task records are stored in SQLite in `tasks` with Task ID, title, description, category, department, assigned to, assigned role, priority, status, due date, created-by user/name/email/role, notes, source, meeting link, and timestamps.
- Task records also store `assigned_user_id` and `assigned_email` when a task is assigned to a registered user.
- Task categories are Admin, IT, Finance, Vendor, Inventory, Travel, Expense, Report, and Other.
- Task priorities are Low, Medium, High, and Critical.
- Task statuses are Open, In Progress, Waiting Approval, Completed, and Cancelled.
- Backend task role scope:
  - `admin` can view and manage all tasks.
  - `it_manager` can view/manage IT tasks and tasks assigned to the IT Manager/team.
  - `finance_manager` can view/manage finance-related tasks and tasks assigned to Finance Manager.
  - `employee` can create task requests and view their own/assigned tasks; employees cannot manage unrelated tasks.
- The Tasks UI includes summary cards for Total Tasks, Open, In Progress, Overdue, and Completed.
- The Task Directory table columns are Task ID, Title, Description, Category, Department, Assigned To, Assigned Role, Priority, Status, Due Date, Created By, Created Date, and Actions.
- Task actions are icon-only View, Edit, Change Status, and Delete; management actions are disabled for roles that cannot manage a given task.
- `Create Task` and `Edit Task` open a modal with Title, Description, Category, Department, Assigned To, Assigned Role, Priority, Due Date, and Notes.
- Assigned To is a dropdown backed by `GET /api/users/assignable`. It shows `Myself` plus role-scoped registered users as `Name - email`, includes a small search field, and saves the selected user's ID, email, display name, and role to the task record.
- Assignable-user scope is enforced in the backend: Admin can assign to all enabled users; IT Manager can assign to IT Manager users/self; Finance Manager can assign to Finance Manager users/self; Employee can assign only to self.
- Creating a task assigned to a registered user creates a targeted notification with type `task.assigned`, title `New task assigned`, task title, assigned-by user, due date when present, and the related task ID. The notification bell and panel show the task assignment notification, and clicking it routes to Tasks.
- Task search filters by task ID, title, description, assigned to, created by, and department.
- Task filters include Status, Priority, Category, Department, Assigned Role, Due Date, My Tasks only, and Overdue only.
- Seeded demo tasks include Admin, IT, Finance, Travel, and Report examples.
- Task API audit events are `task.created`, `task.updated`, `task.status_changed`, and `task.deleted`.

Current Tickets feature status:

- The visible Tickets section uses `/tickets`; legacy `/approvals` still maps to Tickets for refresh compatibility. The page calls the ticket backend through `GET /api/tickets`.
- Ticket data loading is tolerant of a missing `/api/tickets` endpoint during dashboard/session restore, so an older backend cannot trigger a red raw `Not Found` or clear an otherwise valid admin session. A clean restart-backend message is used for raw endpoint 404s.
- The previous Tickets page existed as a renamed Human Ticket/Approval Queue only. It now shows only the unified Ticket Directory UI; the legacy Human Approval Queue and email draft editor are no longer embedded below Tickets.
- Existing approval backend endpoints and dashboard approval workflow remain intact for vendor email and sensitive-action approvals.
- Ticket Directory lists IT and Admin tickets together in one table.
- Ticket table columns are Ticket ID, Title, Type, Category, Priority, Status, Requested by, Assigned to / Assigned role, Created date, Due date, Approval required, and Actions.
- Ticket Type badges display `IT` or `Admin`.
- Ticket filters are Type (`All`, `IT`, `Admin`), Status (`All`, `Open`, `In Progress`, `Waiting Approval`, `Resolved`, `Closed`), and Priority (`All`, `Low`, `Medium`, `High`, `Critical`).
- Ticket search placeholder is `Search tickets...` and filters by ticket ID, title, requester name/email, category, assigned role, and assigned team.
- Ticket row actions are `View`, `Edit`, and `Change status`.
- `Create Ticket` opens a modal for ticket type, category, title, priority, optional due date, required description, and approval-required flag. New tickets are created as `Open`; status changes happen through manager actions.
- Employee users can create both IT and Admin tickets. The backend sets requester name, requester email, requester role, created date, `Open` status, and assigned role/team from the logged-in user plus ticket type/category.
- Successful ticket create/update/status actions upsert the returned ticket into the frontend list immediately, then attempt a full data refresh. This keeps the list responsive even if a later non-auth refresh call fails.
- Ticket creation and status changes refresh the real notification panel data. Created tickets produce `New ticket created: [title]`; resolved tickets produce `Ticket resolved: [title]`; closed tickets and other status changes also create ticket notifications.
- Ticket notifications are stored in SQLite in the `notifications` table with title, message, type, related ticket entity, created timestamp, target requester/role metadata, and per-user read state.
- Notification loading is non-blocking during the main data refresh. If `/api/notifications` is missing on an older backend, the dashboard/tickets/tasks data still loads and notifications fall back to an empty list until the backend is restarted.
- Ticket create accepts either `ticket_type` or `type` in the API payload, stores optional due dates as blank when omitted, and validates title, description, type, category, priority, and approval-required boolean.
- Raw API endpoint 404s still show the restart-backend version-mismatch message, but ordinary resource errors such as `Ticket not found` are no longer mislabeled as backend-version issues.
- `Edit Ticket` and `Change Status` are enabled only for users with ticket manager access.
- Backend ticket role scope:
  - `admin` can view and manage all tickets.
  - `it_manager` can view/manage IT tickets only.
  - `finance_manager` can view/manage finance-related Admin tickets, such as invoice/payment/expense/reimbursement categories.
  - `employee` can create tickets and view only their own tickets.
- Seeded demo IT tickets are Laptop password reset, New software access request, Printer not working, and Device replacement request.
- Seeded demo Admin tickets are Meeting room booking, Vendor invoice follow-up, Office supply request, and Travel booking support.
- Ticket API audit events are `ticket.created`, `ticket.updated`, and `ticket.status_changed`.

Current Expenses feature status:

- Expenses is an implemented internal module at `/expenses`.
- Expense backend endpoints are `GET /api/expenses`, `POST /api/expenses`, `PUT /api/expenses/{expense_id}`, `PATCH /api/expenses/{expense_id}/status`, `POST /api/expenses/import/preview`, and `POST /api/expenses/import/confirm`.
- Expense records are stored in SQLite in the `expenses` table with Expense ID, employee name/email/role, department, category, vendor/merchant, amount, currency, expense date, payment mode, receipt status, receipt attachment name, notes, status, approval-required flag, approved-by, policy exceptions, and timestamps.
- Expense categories are Travel, Food, Hotel, Local Conveyance, Office Supplies, Software, Internet / Phone, Vendor Payment, Client Meeting, Training, and Miscellaneous.
- Expense statuses are Draft, Submitted, Pending Approval, Approved, Rejected, Paid, Reimbursed, and Needs Info.
- The backend derives policy exceptions for amount over policy limit, missing receipt, duplicate receipt, non-refundable ticket, wrong category, and weekend/late-night expense.
- Admin can view/manage all expenses. Finance Manager can view/manage all expenses and approve/reject expenses. Employee can create expenses and view own expenses. IT Manager can view IT-related expenses.
- Employee-created expenses are tied to the logged-in employee even if the submitted payload contains another employee name/email.
- The Expenses UI is focused on the All Expenses table and action row; summary cards are hidden.
- The All Expenses table supports local search/filter, CSV/`.xlsx` Upload Expenses for Admin/Finance Manager, Add/Edit Expense, Approve/Reject actions for Finance Manager/Admin, and local pagination.
- Expense import accepts CSV and `.xlsx` files, rejects legacy `.xls` with a clear message, validates required columns/rows, defaults unknown categories to Miscellaneous with a warning, previews rows before saving, and only persists after Confirm Import.
- Expense search covers expense ID, employee name/email, department, category, vendor/merchant, payment mode, receipt attachment, notes, and status.
- Expense filters include Category, Status, and Department.
- Add/Edit Expense uses a modal form for all requested expense fields and validates employee, email, merchant, amount, expense date, and payment details before saving.
- Expenses page includes the All Expenses table only. Basic Reports, Approval Queue, and Policy Exceptions sections have been removed from the visible Expenses UI.
- Seeded demo expenses include travel, food, vendor payment, software, and office supply examples.
- Expense API audit events are `expense.created`, `expense.updated`, `expense.status_changed`, and `expense.imported`.
- No real payment or reimbursement systems are connected.

Current Travel & Calendar feature status:

- Travel & Calendar is an implemented internal/mock module at `/travel`, not a placeholder.
- Access is role-gated: Admin and Finance Manager can access Travel & Calendar; IT Manager and Employee are blocked by navigation and backend API permissions.
- Travel backend endpoints are `GET /api/travel`, `POST /api/travel`, `PUT /api/travel/{travel_id}`, `GET /api/travel/summary`, `GET /api/calendar-events`, `POST /api/calendar-events`, and `PUT /api/calendar-events/{event_id}`.
- Travel records are stored in SQLite in `travel_records` with Travel ID, employee name/email, department, destination from/to, travel start/end dates, purpose, travel mode, estimated budget, actual spend, number of trips, approval status, policy status, booking status, notes, Google Calendar event ID placeholder, Google sync status placeholder, Google last synced at placeholder, and timestamps.
- Calendar events are stored in SQLite in `calendar_events` with Event ID, title, event type, start/end date-time, location, attendees, related travel ID, reminder, notes, status, Google Calendar event ID placeholder, Google sync status placeholder, Google last synced at placeholder, and timestamps.
- Travel modes are Flight, Train, Bus, Cab, Hotel, Mixed, and Other.
- Travel statuses are Draft, Submitted, Pending Approval, Approved, Rejected, Booked, Completed, Cancelled, and Needs Info.
- Policy statuses are Within Policy, Over Budget, Missing Approval, and Needs Review.
- Calendar event types are Meeting, Vendor Meeting, Travel, Reminder, Internal Event, and Other.
- The Travel & Calendar UI includes dashboard cards for Total travel spend, Upcoming trips, Currently traveling employees, Pending travel approvals, Over-budget travel, and Today's calendar events.
- The page has local search across employee, email, department, destination, purpose, and event title.
- Filters include Department, Travel status, Policy status, Travel mode, and date range; filters also apply to calendar events when they are linked to a travel record.
- Add/Edit Travel Record and Add/Edit Calendar Event use modal forms and persist through the backend.
- Travel tables display dates as `dd/mm/yyyy` and currency as rupees, for example `₹12,500`.
- Summary/report tables show travel count by employee, travel spend by employee, travel spend by department, top destinations, and monthly travel spend.
- Google API readiness is placeholder-only: `google_calendar_event_id`, `google_sync_status`, and `google_last_synced_at` are stored but no real Google OAuth or Google API calls exist.
- Demo travel records and calendar events are seeded on startup and after demo reset when those tables are empty.
- Travel audit events are `travel.created`, `travel.updated`, `calendar_event.created`, and `calendar_event.updated`.

Current Reports feature status:

- Reports is an implemented import/export report management module at `/reports`.
- Access is role-scoped:
  - Admin can view, import, export/download, and delete all reports.
  - IT Manager can view, import, export/download, and delete IT-related reports only.
  - Finance Manager can view, import, export/download, and delete Finance-related reports only.
  - Employee does not have Reports navigation access and cannot import/export/download/delete reports through backend APIs.
- Report backend endpoints are `GET /api/reports`, `POST /api/reports/import`, `GET /api/reports/{id}/download`, `DELETE /api/reports/{id}`, and `GET /api/reports/export`.
- Report metadata is stored in SQLite in `reports` with Report ID, report name, report type, department, uploader user/name/email/role, uploaded date, file type, original file name, local stored file path, file size, status, notes, and timestamps.
- Uploaded report files are stored locally under the runtime database folder at `uploads/reports` using generated safe file names prefixed by the report ID.
- Import Report accepts `.csv`, `.xlsx`, and `.pdf` files from the frontend as base64 payloads, validates file type and empty files, then writes the original bytes to local upload storage.
- Import Report form fields are Report Name, Report Type, Department, and Notes; the UI shows the selected file name before import.
- The Reports table columns are Report ID, Report Name, Report Type, Department, Uploaded By, Uploaded Date, File Type, Status, and Actions.
- Row actions are icon-only: View, Download/Export, and Delete. Delete is disabled when the logged-in role cannot manage that report.
- Top-level Export Reports downloads a CSV of the currently filtered visible report list and respects backend role permissions and filter parameters.
- Reports search covers report name, report type, department, uploaded by, file type, and status.
- Reports filters include Department, Report Type, File Type, Status, and Uploaded Date.
- Demo reports are seeded for IT, Finance, and Admin when the reports table is empty.
- Report audit events are `report.imported`, `report.exported`, and `report.deleted`.

Current vendor feature status:

- Admin users can add/edit/close/reopen vendors and send mock vendor emails.
- IT Manager, Finance Manager, and Employee users cannot manage vendors.
- Vendor fields:
  - vendor name
  - contact person
  - email
  - contact details / phone number
  - office address
  - service provided
  - vendor start date
  - optional vendor end date
  - billing amount
  - billing cycle
- Service Provided defaults to `Choose`; vendor name typing auto-selects obvious service categories only.
- Date fields use native calendar inputs and ISO `yyyy-mm-dd` state; the Vendor Directory displays dates as `dd/mm/yyyy`.
- End date is optional and blank end dates display as `—`.
- Billing stores `billing_amount` and `billing_cycle`.
- Billing amount is numeric-only, required, and must be greater than 0.
- Billing cycle options are Monthly, Quarterly, Half-yearly, and Yearly.
- Vendor Directory displays billing as `₹amount / M`, `₹amount / Q`, `₹amount / HY`, or `₹amount / Y`; confirmed examples include `₹1000 / M`, `₹4322 / Q`, `₹5232 / HY`, and `₹9000 / Y`.
- Add/Edit Vendor normalizes `billing_amount` and `billing_cycle` before calling the backend and verifies the refreshed vendor row with the same normalization.
- Billing cycle aliases/abbreviations such as `M`, `Q`, `HY`, and `Y` are normalized to the canonical cycle labels before save/display checks.
- Vendor page action row has a local `Search vendors...` input, an outlined `Filter` button with funnel icon and chevron, and an icon-only Add Vendor button.
- Vendor search filters the Vendor Directory by vendor name, contact person, email, phone/contact details, service, and office address.
- Vendor filters include Status (`All`, `Active`, `Closed`), Service (`All`, `Transport`, `Food`, `Office Supplies`, `IT Services`, `Security`, `Housekeeping`, `Other`), and Billing cycle (`All`, `Monthly`, `Quarterly`, `Half-yearly`, `Yearly`). The Vendors filter opens as a floating card with pointer, draft filter selections, `Reset`, and `Apply`; filter changes are applied only when Apply is clicked.
- On desktop, vendor search, filter, and Add Vendor share one action row; on smaller screens they stack cleanly.
- Vendors page header follows the reference layout with title/subtitle on the left and local search, filter, and solid purple Add Vendor button on the right.
- Vendor Directory is a large rounded card with an icon, title, subtitle `Manage and view all vendor information`, and a vendor-count badge.
- Vendor table columns are Vendor, Contact, Email, Phone, Service, Start, End, Billing, Status, and Actions. Office Address remains in add/edit forms and mobile details but is removed from the main desktop table to avoid crowding.
- Vendor table uses a soft purple-tinted header row, compact row spacing, thin row borders, bold vendor names, green `ACTIVE` status pills, and muted `CLOSED` status pills.
- Vendor Directory Actions show icon-only buttons in the order Edit, Close/Reopen, then Send.
- Row action buttons use compact outline icon styling: Edit uses pencil purple/blue, Close uses trash red, Reopen uses refresh green, and Send uses paper-plane blue.
- Vendor table/list content scrolls inside a viewport-aware wrapper while the pagination footer remains outside the scrolling area and visible at the bottom of the Vendor Directory card.
- `Send` opens a `Send Email to Vendor` modal with read-only recipient/vendor fields plus subject and message inputs.
- Vendor email sends are mock-only and route through the existing external vendor email approval queue for Admin approval.
- Successful vendor email submit shows `Vendor email sent to approval queue` and records `vendor.email.drafted` plus the standard `approval.queued` audit event.
- Admin can use Send; IT Manager, Finance Manager, and Employee cannot send vendor emails.
- Vendor Directory paginates locally at 10 rows per page with a footer like `Showing 1 to 10 of X vendors`, previous/next arrows, and up to three page buttons with the active page highlighted purple.
- Existing legacy vendor rows without a billing amount can display `— / cycle` until edited with a positive amount.
- Root cause addressed in the latest fix: frontend billing amount/cycle handling was split between the submit path, save verification, and display formatting. The save path now uses the shared formatter helpers instead of raw `Number(...)`/string comparisons.

Current Inventory feature status:

- Inventory is an implemented internal module at `/inventory`, not a placeholder.
- `admin` and `it_manager` can access and manage Inventory. `finance_manager` has read-only Inventory access, and `employee` is blocked from Inventory.
- Inventory uses the same Agent Concierge card/table/action style as Vendors and Settings.
- Inventory main page header shows a Package icon and `Inventory` title without a subtitle or title-adjacent item-count badge.
- Inventory header includes compact centered status summary cards for `In Use`, `Extra`, and `Submitted to Vendor` between the title and search/actions. Counts are computed from the current loaded inventory rows while respecting search and non-status filters, and clicking a status card applies the matching Status filter.
- Inventory no longer shows a separate inner `Inventory List` header or `Add, edit, and import inventory records` subtitle above the table.
- Inventory page action row contains local `Search inventory...`, icon-only Filter, Select dropdown, icon-only Import History, icon-only Import Inventory, and icon-only Add Item controls.
- Inventory search filters by Employee Name, Serial No., Model No., RAM, Disk, Location, Status, and Notes, with legacy fallback matching for older rows.
- Inventory filters include Status and Location.
- Inventory visible fields are Employee Name, Serial No., Model No., RAM, Disk, Location, Status, Notes, and Actions.
- Add Item opens a modal with the new inventory fields and validates Employee Name, Serial No., Model No., RAM, Disk, Location, and Status.
- Edit opens the same modal and updates the existing inventory item.
- Inventory table includes the new compact inventory fields, soft purple sticky header, viewport-aware scrollable list content, status badges, row selection, and local pagination.
- Inventory pagination sits outside the scrolling table/list area in the Inventory table footer with `Showing X to Y of Z items` on the left and compact right-aligned controls: `Page X of Y`, previous arrow, `Go to page...` input, search/go button, and next arrow. The footer remains visible below the internal table scroll area on laptop-sized screens.
- Inventory page jump applies to the current search/filter result, resets to page 1 when search/filter changes, and shows `Page not found` for invalid or out-of-range page numbers.
- Import Inventory opens a visible upload modal with a `Choose File` / `Replace File` button, selected file name display, and clear file-type/empty-file errors.
- Import Inventory also shows `Use the sample template to avoid import errors.` and a `Download Sample Template` button.
- The sample template downloads as `inventory_import_template.csv` with headers `employee_name,serial_no,model_no,ram,disk,location,status,notes`.
- The sample template includes three laptop-style example rows for In Use, Extra, and Submitted to Vendor statuses.
- File input accepts `.csv,.xlsx,.xls`.
- CSV import is supported.
- Excel `.xlsx` import preview is supported through a small backend parser that reads basic workbook XML with Python stdlib, so no new dependency was added.
- Legacy `.xls` files can be selected but are rejected with `Legacy .xls import is not enabled yet. Please use CSV or .xlsx.`
- CSV and `.xlsx` import parse common new headers such as `Employee Name`, `Serial No.`, `Model No.`, `RAM`, `Disk`, `Location`, `Status`, and `Notes`; legacy inventory import headers are still accepted for backward compatibility.
- Import validates required new fields and shows an import preview before saving.
- Import preview table shows all new template fields: Employee Name, Serial No., Model No., RAM, Disk, Location, Status, Notes, and Validation.
- The import preview table is horizontally scrollable so valid imported fields are visible before confirmation.
- If required columns are missing, import preview shows `This file does not match the inventory template. Please download and use the sample template.` instead of flooding the user with row-level required-field errors.
- Inventory table includes row checkboxes and an Actions column with compact icon-only Edit and Delete buttons.
- Inventory row Actions also include an icon-only status update button. It opens a small menu with `In Use`, `Extra`, and `Submitted to Vendor`; selecting a value calls `PATCH /api/inventory/{item_id}/status`, updates the row, shows `Inventory status updated`, and records `inventory.status_updated`.
- Inventory status update is role-gated to `admin` and `it_manager`; `employee` and `finance_manager` cannot update inventory status.
- Inventory status badges include distinct styling for `In Use`, `Extra`, and `Submitted to Vendor`.
- Inventory table header includes a Select All checkbox that selects visible rows on the current page by default.
- Inventory action controls include a `Select` dropdown with `Select current page`, `Select 50 rows`, `Select 100 rows`, and `Select all rows`.
- `Select current page` selects visible rows on the active page; `Select 50 rows` and `Select 100 rows` select the first matching rows from the current filtered list; `Select all rows` selects every row in the current search/filter result across pages.
- When the current page is selected and filtered results continue across pages, Inventory also shows `Select all X inventory items`; this selects every item in the current search/filter result, not unrelated hidden rows.
- Inventory shows a selected-count badge such as `50 selected`, `100 selected`, or `All 463 selected`, and keeps `Delete Selected` visible only when one or more items are selected.
- Changing Inventory search or filters clears existing selections so bulk delete cannot accidentally include hidden rows from a previous view.
- Deleting one item shows `Are you sure you want to delete this inventory item?`; confirmation deletes the backend row and shows `Inventory item deleted successfully`.
- Selecting one or more rows shows the selected count plus `Delete Selected` in the Inventory action row.
- Bulk delete shows `Are you sure you want to delete selected inventory items?` plus the exact count, such as `This will delete 463 inventory items.`
- Bulk delete confirmation deletes selected backend rows through `POST /api/inventory/bulk-delete` and shows `Inventory items deleted successfully`.
- Inventory delete permissions match inventory management permissions: `admin` and `it_manager` can delete; `employee` and `finance_manager` cannot.
- Import batches are tracked for new confirmed CSV/`.xlsx` imports.
- Confirm Import now calls `POST /api/inventory/imports`, creates one batch record for the uploaded file, and stores that batch id on every item created from the file.
- Manual Add Item still stores `import_batch_id = null`.
- Import History can be opened from the Inventory action row.
- Import History shows file name, imported by, imported date, items imported, failed rows, status, and actions.
- Import History actions are `View Items` and `Delete Import`.
- Delete Import confirms `Are you sure you want to delete all inventory items imported from this file?`, deletes only items linked to that `import_batch_id`, marks the batch `Deleted`, refreshes the list, and shows `Import batch deleted successfully`.
- Multiple imported files are supported because every confirmed import creates its own batch record.
- Existing pre-batch rows cannot be reliably distinguished from manual rows because they have `import_batch_id = null`.
- For cleanup of imports created before batch tracking, Import History includes an Admin-only `Legacy unbatched inventory` row when unbatched items exist. Its delete action removes all unbatched inventory items, so it should be used only when those unbatched rows are known to be the bad pre-batch import.
- Inventory audit events include `inventory.item.deleted`, `inventory.items.bulk_deleted`, `inventory.import.created`, and `inventory.import.deleted`.
- `inventory.items.bulk_deleted` audit details include deleted count, selected inventory/item ids, actor, selection mode, search text, and active filter values.
- Imported rows are not persisted until the user clicks Confirm Import.
- Inventory save actions use backend endpoints and audit `inventory.created` and `inventory.updated`.
- No purchase/reorder automation, external inventory system connection, or reorder workflow was added.

Current backend endpoints:

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/users`
- `POST /api/users`
- `PATCH /api/users/{user_id}`
- `POST /api/users/{user_id}/reset-password`
- `DELETE /api/users/{user_id}`
- `GET /api/dashboard`
- `GET /api/approvals`
- `PATCH /api/approvals/{approval_id}`
- `GET /api/tickets`
- `POST /api/tickets`
- `PUT /api/tickets/{ticket_id}`
- `PATCH /api/tickets/{ticket_id}/status`
- `GET /api/audit-log`
- `POST /api/chat/command`
- `POST /api/agent/plan`
- `POST /api/requests/route`
- `GET /api/vendors`
- `POST /api/vendors`
- `PUT /api/vendors/{vendor_id}`
- `PATCH /api/vendors/{vendor_id}/close`
- `POST /api/vendors/{vendor_id}/close`
- `PATCH /api/vendors/{vendor_id}/reopen`
- `POST /api/vendors/{vendor_id}/reopen`
- `POST /api/vendors/{vendor_id}/email`
- `GET /api/travel`
- `POST /api/travel`
- `PUT /api/travel/{travel_id}`
- `GET /api/travel/summary`
- `GET /api/calendar-events`
- `POST /api/calendar-events`
- `PUT /api/calendar-events/{event_id}`
- `GET /api/reports`
- `POST /api/reports/import`
- `GET /api/reports/{id}/download`
- `DELETE /api/reports/{id}`
- `GET /api/reports/export`
- `GET /api/inventory`
- `POST /api/inventory`
- `POST /api/inventory/import/preview`
- `GET /api/inventory/imports`
- `POST /api/inventory/imports`
- `GET /api/inventory/imports/{import_id}/items`
- `DELETE /api/inventory/imports/{import_id}`
- `DELETE /api/inventory/{item_id}`
- `PATCH /api/inventory/{item_id}/status`
- `POST /api/inventory/bulk-delete`
- `PUT /api/inventory/{inventory_id}`
- `POST /api/dev/reset`

Current database/SQLite notes:

- SQLite database defaults to `backend/admin_agent.db`.
- `.gitignore` excludes runtime DB files.
- Schema is created with `CREATE TABLE IF NOT EXISTS`.
- Lightweight compatibility repair exists for the `vendors.billing_amount` column. Vendor create/list/get/update paths ensure legacy vendor tables gain `billing_amount INTEGER NOT NULL DEFAULT 0` before vendor rows are read or written.
- Tickets are stored in the local SQLite `tickets` table with a human-readable `ticket_id`, type, title, category, priority, status, requester, assigned role/team, due date, and approval flag.
- Lightweight compatibility repair exists for the `tickets.requester_role` column. Ticket create/list/get/update paths ensure older local ticket tables gain `requester_role TEXT NOT NULL DEFAULT ''`.
- Inventory items are stored in the local SQLite `inventory_items` table with a unique internal `item_id`, Employee Name, Serial No., Model No., RAM, Disk, Location, Status, Notes, import linkage, timestamps, and legacy compatibility columns for older inventory rows/imports.
- Inventory imports are stored in `inventory_import_batches`; imported inventory rows link back with `inventory_items.import_batch_id`.
- Lightweight compatibility repair exists for optional inventory columns and `inventory_items.import_batch_id` when an older local `inventory_items` table is present.
- Travel records are stored in the local SQLite `travel_records` table with unique `travel_id`, employee/destination/date/spend/status fields, and Google sync placeholder fields.
- Calendar events are stored in the local SQLite `calendar_events` table with unique `event_id`, event schedule/details, related travel ID, and Google sync placeholder fields.
- Reports are stored in the local SQLite `reports` table with unique `report_id`, metadata, uploader, file type/name/path/size, status, notes, and timestamps.
- Uploaded report files are stored under the local `uploads/reports` folder beside the configured SQLite database.
- Demo tickets are seeded on startup and after demo reset when the tickets table is empty.
- Demo inventory items are seeded on startup and after demo reset when the inventory table is empty.
- Demo expenses, Travel & Calendar rows, and reports are seeded on startup and after demo reset when their tables are empty.
- Full migration framework is not implemented.
- Demo seeding repairs built-in demo users on startup if they were disabled or changed locally.

Current AI mode behavior:

- Current AI mode is mock unless a real, non-placeholder `OPENAI_API_KEY` is provided.
- `.env` is local only and must not be committed.
- `.env.example` is safe to commit and contains no real secrets.
- Placeholder keys such as `replace_with_your_openai_api_key`, `your-api-key`, and `your_api_key_here` are treated as missing.
- `OPENAI_MODEL` defaults to `gpt-5.5`.
- If OpenAI client initialization or API calls fail, the planner falls back to mock planning.
- Do not print or expose real API keys or secrets.

Current known bugs/issues:

- No currently confirmed blocking vendor billing bug after the frontend billing normalization fix.
- Existing legacy vendor rows that were created before `billing_amount` can show `— / cycle` until edited.
- Authentication is demo-only and stores plain demo passwords in SQLite.
- No production SSO, password hashing, secure cookie sessions, deployment setup, Docker setup, CI, frontend unit tests, or browser E2E tests are confirmed.
- Only Vendor Review Meeting has confirmed end-to-end workflow execution.
- Travel & Calendar is now implemented as an internal/mock module with no real Google or travel vendor integrations. Some other modules remain planning/routing-only, and Inventory has internal add/edit/import management but not purchase automation or external integrations.
- Email/WhatsApp connector sends require a user preview/confirm step and role permission checks, but Conci AI does not yet execute send commands end-to-end; it should prepare drafts/preview data rather than auto-send sensitive external messages.
- OpenAI planner mode requires a real API key and network/API availability; transcript summarization OpenAI mode is not production-confirmed.
- `VITE_API_BASE_URL` is supported in frontend code but not yet documented in README.

Current run commands:

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev

# Backend tests from repo root
backend/.venv/bin/python -m pytest backend/tests

# Frontend production build
cd frontend
npm run build

# Frontend billing formatter test
cd frontend
node src/vendorBilling.test.mjs
```

Latest test results:

- Backend tests: `146 passed in 16.69s` after adding per-user connector ownership and role-based connector access tests.
- Frontend build: `npm run build` passed after exposing Settings/Connectors to all roles; latest bundles include `dist/assets/index-xjoPrbJO.css` and `dist/assets/index-04XrW8Z8.js`.
- Frontend navigation access test: `node src/navigationAccess.test.mjs` passed after adding Settings to Finance Manager navigation.
- Frontend billing formatter test: `node src/vendorBilling.test.mjs` passed, including `₹1000 / M`, `₹4322 / Q`, `₹5232 / HY`, and `₹9000 / Y`.
- No smoke tests were run during the connector work; manual browser testing is left to the user.

Next recommended task:

- Add focused frontend/browser smoke tests for login, route-any-request, Vendor Review Meeting, vendor creation/edit/close/reopen, approval permissions, and logout.

## 1. Product Goal

AI Admin Agent MVP is a local FastAPI + React application for automating internal administrative workflows while keeping risky actions behind human approval.

The main demo workflow is Vendor Review Meeting automation:

- Understand a user request.
- Create an AI Admin Agent execution plan.
- Run mocked admin tools for meeting preparation, reminders, notes, tasks, and follow-up.
- Queue external vendor communication for human approval.
- Update the dashboard and audit log.

All external integrations are currently mocked. The app must not connect to real Gmail, Calendar, Slack, Teams, Jira, ServiceNow, payment, travel, or vendor systems until explicitly implemented later.

## 2. Current Stack

Backend:

- Python
- FastAPI
- Pydantic
- SQLite
- Uvicorn
- OpenAI Python SDK dependency is present
- `python-dotenv` for local environment loading

Frontend:

- React
- Vite
- `lucide-react` icons
- Plain CSS in `frontend/src/styles.css`

Testing:

- `pytest`
- Tests live in `backend/tests/test_vendor_workflow.py`

Database:

- SQLite database defaults to `backend/admin_agent.db`
- Runtime database file is ignored by git

## 3. Current Implemented Features

Confirmed implemented backend features:

- FastAPI app factory in `backend/app/main.py`
- SQLite repository in `backend/app/repositories/admin_repository.py`
- Demo user seeding
- Login, logout, and current-user endpoints
- Bearer-token session handling
- Protected dashboard, approval, audit, mock-data, agent-plan, and chat-command endpoints
- Admin-only user management endpoints
- AI agent planning endpoint at `POST /api/agent/plan`
- Request routing endpoint at `POST /api/requests/route`
- Task management endpoints at `GET /api/tasks`, `POST /api/tasks`, `GET /api/tasks/{id}`, `PUT /api/tasks/{id}`, `PATCH /api/tasks/{id}/status`, and `DELETE /api/tasks/{id}`
- Vendor directory endpoints at `GET /api/vendors` and `POST /api/vendors`
- Ticket directory endpoints at `GET /api/tickets`, `POST /api/tickets`, `PUT /api/tickets/{ticket_id}`, and `PATCH /api/tickets/{ticket_id}/status`
- Main command endpoint at `POST /api/chat/command`
- Vendor Review Meeting workflow execution
- Approval queue for external vendor emails
- Central backend approval rules and routing service
- Role-based approval permission checks
- Role-based task visibility/manage permission checks for Admin, IT Manager, Finance Manager, and Employee users
- Role-based ticket visibility/manage permission checks for Admin, IT Manager, Finance Manager, and Employee users
- Notification endpoints at `GET /api/notifications`, `PATCH /api/notifications/{notification_id}/read`, and `PATCH /api/notifications/read-all`
- Ticket events create notifications for `ticket.created`, resolved/closed status changes, and other status changes.
- Notification visibility follows ticket visibility: Admin sees all ticket notifications, IT Manager sees IT ticket notifications, Finance Manager sees finance-related Admin ticket notifications, and Employee sees notifications for their own tickets.
- Notification read/unread state is tracked per user through the notification read-user list, so marking a notification read for one user does not mark it read for every role/user.
- Role-based vendor permission checks; `admin` can list/create/edit/close/reopen/send vendor emails, `finance_manager` can list vendors read-only, and other roles are blocked from vendor data/actions
- Role-based Travel & Calendar permission checks; `admin` and `finance_manager` can access/manage internal travel records and calendar events, while `it_manager` and `employee` are blocked
- Travel & Calendar endpoints and analytics summary for travel spend, upcoming/current trips, approvals, over-budget records, today's events, employee/department/destination/monthly summaries, and Google sync placeholder fields
- Role-based Reports permission checks; `admin` can manage all reports, `it_manager` can manage IT reports only, `finance_manager` can manage Finance reports only, and `employee` cannot import/export/download/delete reports
- Reports import/export/download/delete endpoints with local file storage and filtered CSV export
- Audit logging for important AI and human actions
- Audit logging for `vendor.created`
- Demo reset endpoint for admins at `POST /api/dev/reset`

Confirmed implemented frontend features:

- Polished compact split-screen Agent Concierge login page with left brand/feature panel and right login form section; final target sizing is 880px wide by 640px tall, 380px left section, 500px right section, 390px-wide form controls, 38px headline, 28px welcome title, and 44px inputs/buttons
- Login screen opens with empty email/password fields by default; demo credentials are not shown on the login screen
- Login fields include Mail/Lock icons, password visibility toggle, Remember me checkbox, forgot-password demo message, and Google demo-mode message
- Internal operations dashboard layout
- Top horizontal navigation
- Top search bar
- Real notification bell unread badge and notification dropdown
- AI mode badge
- Logged-in user identity display
- Logout button
- Role-based Dashboard command center:
  - Admin sees Total Tickets, Open Tasks, Active Vendors, Inventory Items, Monthly Expenses, Pending Approvals; charts for Tickets by Status, Tasks by Status, Expenses by Month, Inventory by Status; sections for Recent Tickets, Pending Approvals, and Recent Activity; quick actions for Create Ticket, Add Vendor, Add Inventory, Upload Expense, and Import Report.
  - IT Manager sees Open IT Tickets, In Progress Tickets, Resolved Tickets, Inventory In Use, Extra Inventory, Submitted to Vendor; charts for IT Tickets by Status, IT Tickets by Category, and Inventory by Status; sections for Recent IT Tickets, Inventory Status, and IT Tasks; quick actions for Create Ticket, Add Inventory, and Import Inventory.
  - Finance Manager sees Monthly Expenses, Pending Expenses, Approved Expenses, Travel Spend, Vendor Bills, Finance Tasks; charts for Expenses by Category, Expenses by Month, Travel Spend by Month, and Vendor Billing; sections for Expense Exceptions, Pending Finance Approvals, and Recent Travel Records; quick actions for Upload Expense, Add Travel Record, and Export Report.
  - Employee sees My Tickets, My Tasks, Waiting Approval, Completed; sections for My Recent Tickets, My Tasks, and My Requests; quick actions for Create Ticket and Create Task Request.
- Human Ticket Queue with approve, edit, and cancel controls
- Role-based disabled approval buttons
- Unified Ticket Directory for IT/Admin tickets with local search, filters, Create Ticket, View, Edit, and Change status controls
- Full Task Directory for Admin/IT/Finance/Employee tasks with summary cards, search, filters, Create Task, View/Edit/Change Status/Delete icon actions, role-scoped controls, and pagination
- Notification panel lists recent ticket notifications with title, message, timestamp, unread/read state, click-to-mark-read behavior, and `Mark all as read`.
- Tasks, Tickets, Vendors, Travel & Calendar, Expenses, Inventory, Reports, and Settings navigation sections, filtered by logged-in role
- Travel & Calendar page with smart dashboard cards, travel records table, calendar events table, add/edit modals, local search/filters, and analytics summary cards/tables
- Reports page with report list/table, Import Report modal, top-level filtered Export Reports CSV action, per-row View/Download/Delete icon actions, local search, and Department/Type/File Type/Status/Uploaded Date filters
- Vendors page includes an Admin-only Add Vendor modal with required-field validation and a persisted vendor directory table
- Admin user management UI in Settings

Confirmed frontend session behavior:

- Auth tokens are stored only in `sessionStorage` as `admin_agent_token`.
- Legacy `localStorage` auth tokens are ignored and removed during auth initialization and token writes.
- Session restore runs before protected route rendering and only clears tokens for true auth failures.
- A browser refresh in the same tab on a supported route should keep the logged-in user on that route until logout.
- A new/shared browser tab without a valid sessionStorage token shows the login screen first, then returns to the requested allowed route after successful login.

## 4. Current AI Mode Behavior

The app has two planning modes:

- Mock AI mode: deterministic local planning
- OpenAI planner mode: uses OpenAI Responses API structured planning when a real API key is configured

Current behavior confirmed from `backend/app/core/config.py` and `backend/app/services/agent_planner.py`:

- The app loads environment variables from repo-root `.env` and `backend/.env` if those files exist.
- If `OPENAI_API_KEY` is missing, planning uses `MockAdminAgentPlanner`.
- If `OPENAI_API_KEY` is one of the known placeholder values, it is treated as missing.
- If a non-placeholder `OPENAI_API_KEY` exists, planning uses `OpenAIResponsesAdminAgentPlanner`.
- If the OpenAI client or API call fails, the planner falls back to mock planning and marks `last_mode` as `mock_agent_planner_fallback`.
- `OPENAI_MODEL` defaults to `gpt-5.5`.

Current AI mode is mock unless a real `OPENAI_API_KEY` is provided.

The transcript summary adapter remains mock-first unless `USE_OPENAI_AI=true` is set. The exact production readiness of OpenAI transcript summarization is not confirmed in repo.

## 5. Environment Variables

Committed example file:

- `.env.example`

Local-only file:

- `.env`

Important rule:

- `.env` is local only and must not be committed.
- `.env.example` is safe to commit.
- Do not print or expose real API keys or secrets.

Variables documented in `README.md` and config:

```text
OPENAI_API_KEY       Optional. Enables OpenAI Responses API agent planning when set to a real value.
OPENAI_MODEL         Optional. Defaults to gpt-5.5.
USE_OPENAI_AI        Optional. Defaults to false. Enables the OpenAI transcript summary adapter.
ADMIN_AGENT_DB       Optional. SQLite database path. Defaults to backend/admin_agent.db.
```

Placeholder values treated as missing:

```text
replace_with_your_openai_api_key
your-api-key
your_api_key_here
```

## 6. Demo Credentials

Seeded automatically by `AdminRepository.seed_demo_users()`:

```text
admin@company.com / admin123 / admin / Admin User
it@company.com / it123 / it_manager / IT Manager
finance@company.com / finance123 / finance_manager / Finance Manager
employee@company.com / employee123 / employee / Employee User
```

This is demo authentication only. Production auth must be replaced with Google/Microsoft SSO, hashed passwords, secure sessions, RBAC, and audit-grade logging.

## 7. Admin Task Scope

Supported AI Admin Agent task types are defined in `backend/app/services/agent_planner.py`:

```text
meeting_management
reminder_management
meeting_notes
task_tracking
document_management
report_generation
approval_followup
inventory_management
travel_management
expense_management
it_request
floor_activity_management
vendor_management
```

Request routing task types are handled by `backend/app/services/approval_rules.py`:

```text
meeting_management
vendor_management
expense_management
travel_management
inventory_management
it_request
document_management
report_generation
floor_activity_management
```

Every routed request receives:

```text
task_type
priority
risk_level
status
requester_user_id
assigned_role
required_approval_roles
approval_required
approval_reason
```

Current full execution workflow is confirmed for Vendor Review Meeting only. Other task types are currently planning-oriented, routed through the backend rules engine, or represented as dashboard/module placeholders unless otherwise implemented in code.

## 8. Automation Levels

Supported automation levels:

```text
automatic
needs_human_approval
human_decision_required
```

Meaning in current product:

- `automatic`: safe mocked admin action can proceed without approval.
- `needs_human_approval`: the agent can prepare outputs, but a human must approve before the risky action is executed.
- `human_decision_required`: the request is high-risk, ambiguous, legal/compliance related, emergency/safety related, or a policy exception; a human decision is required before execution.

## 9. Human Approval Rules

Role rules confirmed in `README.md`, `auth_service.py`, `approval_service.py`, and repository approval serialization:

- `admin`: can access Dashboard, Vendors, Tasks, Tickets, Travel & Calendar, Expenses, Inventory, Reports, and Settings; can manage users and roles, manage vendors, manage inventory, view/manage all tasks and tickets, and approve all requests.
- `finance_manager`: can access Dashboard, Travel & Calendar, Reports, Tasks, Tickets, Vendors, Inventory, and Settings; can view Vendors/Inventory read-only, view/manage finance-related tasks and finance-related Admin tickets, manage their own Email/WhatsApp connectors, and approve expense, payment, invoice mismatch, and reimbursement approvals; cannot approve vendor/legal/IT actions or manage vendors/inventory.
- `it_manager`: can access Dashboard, Inventory, Tasks, Tickets, Reports, and Settings; can view/manage IT tasks and IT tickets, manage inventory, and approve IT support, account access, device, password workflow, and IT equipment approvals; cannot approve finance/vendor/legal actions.
- `employee`: can access Dashboard, Tickets, Settings/account, and Tasks; can create task requests and IT/Admin tickets, view own/assigned tasks and own tickets, and cannot approve sensitive actions or manage users.

Approval role mapping currently includes:

- Expense approval, payment, invoice mismatch, reimbursement -> Finance Manager/Admin.
- External vendor follow-up email, meeting approval, travel booking, inventory reorder, floor activity -> Admin.
- IT support, account access, device request, password request -> IT Manager/Admin.
- IT equipment inventory reorder -> IT Manager/Admin.
- Vendor contract changes/renewals, confidential document sharing, file deletion, legal/compliance decisions, and policy exceptions -> Admin.

Approval request metadata includes:

- `required_roles`
- `required_role_label`
- `assigned_role`
- `task_type`
- `priority`
- `risk_level`

The frontend disables approval controls when the current user does not have permission.

The reusable approval rules engine is `backend/app/services/approval_rules.py`. It centralizes approval role mapping, default request assignment, request priority, risk, and approval reason generation. `AdminRepository._approval_from_row()` uses this service when serializing approvals, so the frontend relies on backend-provided `required_roles` and `required_role_label` instead of hardcoded approval logic.

`POST /api/requests/route` classifies and routes a new request, stores it in `routed_requests`, and records `request.routed` plus `approval.rule.applied` audit events when approval is required.

The frontend calls this endpoint through `frontend/src/api.js::routeRequest()`. The dashboard `Route Any Request` panel lets users enter free-text requests such as invoice mismatches, vendor follow-ups, password/device/account requests, travel bookings, file deletion, confidential sharing, inventory reorders, and simple reminders. The frontend displays only backend-provided routing fields and does not duplicate approval rules in UI code. Dashboard payloads include recent routed requests as `routed_requests`.

## 10. Safety Rules

Human approval is required for:

- External vendor emails
- Payments
- Expense approvals
- Travel bookings
- Contract changes
- Confidential document sharing
- File deletion
- Legal/compliance decisions
- Emergency/safety decisions
- Policy exceptions

Current policy behavior confirmed in `backend/app/services/policy.py`:

- File deletion requires approval and must never run automatically.
- Legal/compliance decisions require human review.
- Emergency or safety decisions require a human decision.
- Policy exceptions require human review.
- Emergency/safety decisions are classified as critical risk.
- External vendor email alone is classified as medium risk.

Auto-allowed actions currently include:

```text
calendar_hold
agenda_preparation
internal_reminder
meeting_notes
task_creation
dashboard_update
```

Every important action should be logged in `audit_logs`.

## 11. Vendor Review Meeting Workflow

Main user request:

```text
Plan tomorrow's vendor review meeting, remind everyone, prepare files, take notes during the meeting, and follow up on action items.
```

Workflow confirmed in `backend/app/services/workflow.py`:

1. Create a chat run.
2. Audit `chat.command.received`.
3. Create an AI Admin Agent plan.
4. Store the agent plan in `agent_plans`.
5. Route the request through the backend approval rules engine.
6. Store the routed request in `routed_requests`.
7. Audit `agent.plan.created`, `request.routed`, and `approval.rule.applied` when relevant.
8. If the request is not a vendor meeting workflow, stop at planned-only.
9. Load mock context from `backend/app/data/mock_data.py`.
10. Generate agenda using mock AI.
11. Audit `agenda.prepared`.
12. Create scheduled meeting with mock vendor, attendees, agenda, and files.
13. Audit `meeting.scheduled`.
14. Generate internal reminder.
15. Audit `reminder.generated`.
16. Summarize mock transcript.
17. Audit `meeting_notes.generated`.
18. Extract decisions.
19. Audit `decisions.extracted`.
20. Extract action items and create tasks.
21. Audit `action_items.created`.
22. Store meeting notes.
23. Draft vendor follow-up email.
24. Audit `external_email.drafted` with Admin approval required.
25. Queue approval for external vendor email.
26. Audit `approval.queued`.
27. Audit `dashboard.updated`.
28. Mark run completed.
29. Audit `workflow.completed`.

The external vendor follow-up email is not auto-sent. It must be approved by an authorized human.

## 12. Current UI Direction

Current frontend direction is an internal admin automation dashboard for an operations-led demo.

Confirmed UI elements:

- Visible product branding uses `Agent Concierge`.
- Top-left logo initials are `AC`.
- Top horizontal navigation replaces the old desktop left sidebar.
- The header uses the Agent Concierge reference shell with a brand block, large global search, notification bell, sun/moon theme toggle, and profile menu.
- Top search bar with placeholder `Search anything...`.
- User profile/name/email/role in the top area with initials avatar and account dropdown.
- Logout button is inside the user account dropdown.
- AI mode badge: Mock AI Mode or OpenAI Mode
- Dashboard card layout with role-based summary cards, chart grid, quick actions, and recent-work sections.
- Admin/IT/Finance dashboard charts are backed by the role-filtered dashboard API; Employee dashboard intentionally omits charts.
- Ticket Directory for unified IT/Admin tickets with search, Type/Status/Priority filters, count badge, Create Ticket, View/Edit/Change status actions, and responsive horizontal table scrolling
- Settings/Users table for admin-created users only, with search, Role filter, Add User modal, inline edit/save, real delete confirmation, more-menu password reset, count badge, and pagination footer
- Full Tasks page with summary cards, Task Directory table, local search/filter controls, Create Task modal, View/Edit/Change Status/Delete icon actions, role-scoped controls, and local pagination
- Dashboard empty states appear when a role has no tickets, tasks, approvals, expenses, travel records, inventory data, or audit activity.

Current operations-demo styling status:

- The app uses a light enterprise/admin visual style: white/off-white workspace, top horizontal navigation, soft borders, rounded cards, subtle shadows, and purple/blue accents.
- The top utility row uses a larger AC gradient logo, `Agent Concierge` product name, `Search anything...`, command-key hint, notification icon with red badge, sun/moon theme toggle, divider, and logged-in user chip.
- The section navigation is a rounded horizontal row below the utility controls and is role-filtered. The old desktop left sidebar/collapse control has been removed.
- The top search submits to the best matching allowed section and filters visible dashboard data, tasks, tickets/approvals, vendors, expenses, and audit items by the typed query.
- The notification icon opens a real notifications dropdown. The badge shows the unread notification count only, with no static fallback count.
- Notification rows show title, message, timestamp, and unread/read state. Clicking a ticket notification marks it read and routes to Tickets. `Mark all as read` clears all visible unread notifications for the current user.
- Section navigation uses URL paths, so refreshing `/vendors`, `/approvals`, `/tasks`, and other supported sections preserves the section instead of returning to Dashboard.
- The logged-in user chip shows initials avatar, name, email, role, and opens an account panel with Logout.
- Dashboard contains role-specific summary cards, Recharts charts, quick actions, and recent-work sections rather than the old automation-heavy demo cards.
- Empty states are polished for dashboard tickets, tasks, approvals, expenses, inventory, travel, and activity sections.
- Vendor Review Meeting workflow backend code remains available, but the current Dashboard UI is focused on role-based operational summaries rather than the old Ask Agent Concierge / Route Any Request panels.
- Light mode is the default theme.
- Dark mode is supported through a sun/moon toggle in the top header.
- Theme preference is stored in `localStorage` as `admin_agent_theme` and restored on reload.
- Dark mode uses the previous Agent Concierge dark-mode contrast behavior with accent styling and readable inputs/cards.
- The dashboard cards use screenshot-inspired headers, View all actions, row-based content, and footer links.
- The Human Ticket Queue is visually emphasized on the dashboard and keeps role-based approval controls.
- The layout is responsive for laptop demos and collapses navigation/card grids on smaller screens.
- The UI is an application dashboard, not a marketing landing page.

Current demo verification status:

- Frontend build passes (`npm run build`; latest assets `dist/assets/index-cGkNpVP-.css` and `dist/assets/index-BgsRPhQk.js`).
- Frontend focused Node checks pass (`node src/authStorage.test.mjs`; `node src/navigationAccess.test.mjs`; `node src/vendorBilling.test.mjs`).
- Backend tests pass (`backend/.venv/bin/pytest backend/tests/test_vendor_workflow.py`; latest run: `129 passed in 13.24s`).
- Local API smoke test reset the demo, confirmed Run Automation completes the Vendor Review Meeting workflow, creates meeting notes and 3 tasks, and leaves 1 vendor follow-up email pending for human approval.
- Backend tests cover admin login/current user/dashboard/tickets availability, normalized demo user login, admin user/role editing, non-admin user edit blocking, task create/edit/status/delete/audit logging, task role scoping, employee task creation, task validation, vendor create/list, required-field validation, role blocking for non-admin users, vendor email approval queueing, vendor audit logging, seeded ticket visibility, employee IT/Admin ticket creation, own-ticket visibility, employee status-change blocking, ticket required-field validation, ticket audit logging, ticket notification creation/resolution/read-state behavior, ticket table compatibility repair, IT Manager ticket management, Finance Manager finance-ticket management, role-scoped approval listing, employee approval blocking, and finance-related Admin ticket visibility.

Required navigation currently present:

```text
Dashboard
Vendors
Tasks
Tickets
Travel & Calendar
Expenses
Inventory
Reports
Settings
```

Meetings has been removed from top navigation and `/meetings` is redirected to Dashboard. Travel & Calendar now supports internal travel records, calendar events, analytics, and Google sync placeholder fields only. Inventory supports internal inventory list, manual add/edit, CSV/`.xlsx` import preview/confirmation, delete, bulk delete, status updates, and import batch management; full purchase/reorder workflows are not implemented.

Dashboard command center behavior:

- `GET /api/dashboard` now returns role-based `summary_cards`, `quick_actions`, `charts`, tickets, tasks, pending approvals, audit logs, reports, expenses, travel records, inventory items, vendors, and `vendor_billing_dashboard` in addition to existing metrics, meetings, plan, and routed-request data.
- Dashboard role scoping is enforced in the backend: Admin sees all dashboard data; IT Manager sees IT tickets/tasks plus inventory/report activity and vendor service summary without billing amounts; Finance Manager sees finance expenses/travel/vendor/report/task data including vendor billing; Employee sees only their own tickets, tasks, waiting requests, and activity and receives no vendor billing dashboard.
- Admin summary cards include Total Tickets, Open Tasks, Active Vendors, Inventory Items, Monthly Expenses, and Pending Approvals.
- IT Manager summary cards include Open IT Tickets, In Progress Tickets, Resolved Tickets, Inventory In Use, Extra Inventory, and Submitted to Vendor.
- Finance Manager summary cards include Monthly Expenses, Pending Expenses, Approved Expenses, Travel Spend, Vendor Bills, and Finance Tasks.
- Employee summary cards include My Open Tickets, My Tasks, Waiting Approval, and Completed Tasks.
- Quick Actions are role-specific: Admin gets Create Ticket, Add Vendor, Add Inventory, Upload Expense, and Import Report; IT Manager gets Create Ticket, Add Inventory, and Import Inventory; Finance Manager gets Upload Expense, Add Travel Record, and Export Report; Employee gets Create Ticket and Create Task Request.
- Admin dashboard charts are Tickets by Status, Tasks by Status, Expenses by Month, and Inventory by Status.
- IT Manager dashboard charts are IT Tickets by Status, IT Tickets by Category, and Inventory by Status.
- Finance Manager dashboard charts are Expenses by Category, Expenses by Month, Travel Spend by Month, and Vendor Billing.
- Employee dashboard receives an empty `charts` array and does not render dashboard charts.
- The Vendor Billing Dashboard section shows current active vendors, vendor service counts, vendor-wise current billing, total current monthly-equivalent billing, expected billing for this month/next month/current quarter/current year, closing-soon vendors, and a bottom smart vendor chatbot.
- The smart vendor chatbot is local/mock-only and answers from already-loaded vendor dashboard data. It handles active vendors, food vendors, monthly vendor billing, highest billing, expected billing this month, service summary, and vendors closing soon. No external OpenAI or third-party API call is required for this chatbot.
- Dashboard uses a theme-aware command-center treatment. Light mode uses the same light Agent Concierge surfaces as the rest of the app, while dark mode keeps the dark navy/black command-center treatment. On desktop it uses a two-column layout with roughly 65% main dashboard content on the left and a sticky right-side `Conci AI` chat panel around 35% width. On smaller screens, the assistant moves below the dashboard content.
- Dashboard quick actions now sit below the summary cards, charts render in a compact two-column grid on desktop, and Admin-only Recent Tickets, Pending Approvals, Recent Activity, and Vendor Billing Dashboard appear as compact bottom action cards that open detail modals.
- IT Manager Dashboard uses the same theme-aware command-center shell, renders IT charts as a compact three-card row on desktop, and shows bottom compact cards for Recent Tickets, Pending Approvals, Recent Activity, and Vendor Billing Dashboard; those cards open role-scoped detail modals and do not expose finance expense details or admin-only user data.
- Finance Manager Dashboard uses the same theme-aware command-center shell, omits the quick-action row to match the Finance reference layout, places compact action cards directly below the summary row, renders finance charts in a reduced-height two-by-two grid, shows Expense Exceptions/Pending Finance Approvals/Recent Travel Records lower on the page, and keeps Vendor Billing Dashboard in the compact cards/modal flow. The finance compact cards use finance-scoped tickets, approvals, audit logs, and vendor billing data and do not expose IT-only or admin-only user/settings data.
- Employee Dashboard uses the same theme-aware command-center shell, shows four personal summary cards in one row on desktop, keeps Create Ticket and Create Task Request quick actions, shows My Recent Tickets/My Tasks/My Requests, and adds bottom compact cards for Recent Tickets, Pending Approvals, Recent Activity, and My Pending Requests. Employee compact cards open modals backed only by the employee's own visible tickets, tasks, pending request status, and activity.
- The `Conci AI` panel has a sparkle icon, title/subtitle, refresh-context, expand/collapse, trash/clear-chat, and close controls, an open-again button when closed, timestamps, right-aligned purple user messages, left-aligned theme-aware assistant messages, and role-aware suggestion chips. The previous footer note `Conci AI responses may be inaccurate.` has been removed from the UI.
- `Conci AI` sends user messages to `POST /api/chat/assistant`; the older `POST /api/chatbot/ask` route remains as a compatibility alias. The assistant endpoint accepts normal JSON chat requests and browser `multipart/form-data` chat requests with an attached file. It identifies the logged-in user from the bearer token, filters app data with the same backend role helpers used by the app pages, and returns safe `answer`, `bullets`, `source`, and optional compact `table` fields.
- Chat input is a controlled editable multiline composer: users can click, type, select, delete, copy/paste, and edit before sending; Enter sends, Shift+Enter inserts a new line; blank sends are blocked; the send button is disabled while an answer is loading; input text is cleared only after successful text submission. Chat history and pending draft text are stored in parent state and `sessionStorage`, so resizing, closing/reopening, and returning to Dashboard do not wipe the conversation.
- User-sent Conci AI messages show a small edit action on hover/focus. Editing loads that user message back into the composer, shows an editing banner with Cancel, replaces only the selected user message, removes its linked assistant response, and resends the edited text. New chat turns store a request id so edited messages can remove the correct assistant response; older saved turns fall back to removing the immediately following assistant reply. Assistant messages are not editable.
- The Conci AI refresh icon silently reloads dashboard/chat context through the normal dashboard refresh flow and does not clear messages, typed input, or session history. Clearing chat is a separate trash header action and requires confirming `Are you sure you want to clear this chat?`.
- The chat composer includes a file attachment button. Selected files show their name before sending and appear on the sent user message. CSV and `.xlsx` attachments are parsed temporarily on the backend using the existing lightweight spreadsheet parser; TXT files are decoded as text; PDF uploads return a clear `PDF reading is not supported yet` message. File answers include file name/type, data row or line count, detected columns/headers, sample records, missing inventory-template columns when applicable, and simple file search results. File responses are returned directly without also sending the generic chatbot fallback.
- `Conci AI` uses local rule-based responses from existing app data when OpenAI mode is not configured. If OpenAI mode and an API key are available, the backend may use OpenAI only to refine the already role-filtered answer and bullets; hidden unauthorized rows are never sent to the frontend or model.
- `Conci AI` now has a backend intent layer before answer generation. User input is normalized, common spelling mistakes are corrected, and local fuzzy matching maps alternate wording or typos to known intents such as recent/open/my tickets, pending approvals, open/my tasks, vendor billing, active vendors, inventory summary, monthly expenses, travel spend, reports, and help. If OpenAI mode is configured, the backend may use OpenAI only to classify the intent from the user message and allowed intent labels, never with unauthorized app rows.
- The backend rule engine answers natural-language questions about dashboard summaries, users, vendors/vendor billing, tickets, tasks, inventory, expenses, travel/calendar, reports, approvals, and audit/recent activity. It also handles casual conversation such as `what’s your name?`, `who are you?`, `hi`, `how are you?`, `what can you do?`, `thank you`, gender questions, human/real questions, and `who made you?` as `Conci AI`. Answers use short text, bullets for lists, rupee formatting, dd/mm/yyyy dates, and `I couldn’t find matching data for your access level.` when no visible data matches.
- Vendor and vendor-billing chatbot answers can include a compact table payload, and the Dashboard chat bubble renders those rows as a small theme-aware table inside the assistant message.
- Pending approval questions use dedicated approval responses instead of the generic no-data answer: pending approvals return `Here are your pending approvals:` with title, type/category, requested by, priority, and created date; empty approval queues return `You don’t have any pending approvals right now.`; approval access failures return `You do not have access to approval data.`
- Empty ticket/task/vendor/inventory/expense answers now use module-specific text such as `You don’t have any open tickets right now.`, `You don’t have any open tasks right now.`, `No vendors found for that request.`, `No inventory items found for that request.`, and `No expenses found for that request.`
- Unknown non-data questions fall back to `I’m not sure what you mean. You can ask me about tickets, tasks, approvals, vendors, inventory, expenses, travel, or reports.`
- `Conci AI` answers respect role-scoped dashboard data: Admin can ask about everything; IT Manager can ask about IT tickets/tasks, inventory/devices/assets, IT reports, IT approvals, and recent IT activity; Finance Manager can ask about expenses, travel/calendar, vendor billing, finance tasks/tickets/reports, finance approvals, and inventory summary; Employee can ask only about their own tickets/tasks/waiting requests/recent activity.
- Dashboard prompt chips are role-aware: Admin sees pending approvals/vendor billing/open tickets/inventory/monthly expenses prompts; IT Manager sees IT ticket/inventory/device/IT task prompts; Finance Manager sees monthly expenses/vendor billing/travel spend/finance approval prompts; Employee sees own tickets/tasks/pending request prompts.
- Unauthorized chatbot requests return `You do not have access to that information.` and do not expose hidden rows to the frontend.
- Frontend Dashboard cards use the Agent Concierge style with summary cards at top, charts below summaries, role sections below charts, responsive 3/2/1-column layouts, tooltips, readable labels, and empty states when no data exists.

Inventory page current behavior:

- Inventory is accessible from the top navigation at `/inventory` for `admin`, `it_manager`, and `finance_manager`.
- Admin and IT Manager can add/edit/import/delete/update inventory status. Finance Manager has read-only Inventory access. Employee is blocked from Inventory.
- Inventory uses a header/action row with local search, Filter, Import Inventory, and Add Item.
- Search filters by Employee Name, Serial No., Model No., RAM, Disk, Location, Status, and Notes.
- Filters cover Status and Location.
- The Inventory table shows Employee Name, Serial No., Model No., RAM, Disk, Location, Status, Notes, and Actions, with local pagination.
- `Add Item` opens a modal with the new inventory fields and saves through `POST /api/inventory`.
- `Edit` opens the same modal and saves through `PUT /api/inventory/{inventory_id}`.
- Row `Delete` opens a confirmation and deletes through `DELETE /api/inventory/{item_id}`.
- Row checkboxes support selected bulk deletion through `POST /api/inventory/bulk-delete`.
- Delete actions are available only to Admin and IT Manager.
- `Import History` opens the import batch table.
- New confirmed imports are saved as batches with file name, importing user, timestamp, total rows, successful rows, failed rows, status, and notes/errors.
- `View Items` shows all active inventory items linked to a selected import batch.
- `Delete Import` removes all active inventory items linked to that import batch and marks the import batch `Deleted`.
- Manual inventory items are not linked to import batches and are not deleted when a normal import batch is deleted.
- A special Admin-only `Legacy unbatched inventory` history row appears when items with `import_batch_id = null` exist. This is the cleanup path for older imports created before batch tracking, but it can include manual items because old rows do not have enough metadata to distinguish source.
- Import Inventory opens a modal with a visible `Choose File` button, selected file name display, Replace File behavior, and inline errors.
- The import modal includes `Download Sample Template`, which downloads `inventory_import_template.csv` containing `employee_name,serial_no,model_no,ram,disk,location,status,notes` plus three sample rows.
- CSV and `.xlsx` imports validate required new fields, show a preview, and persist rows only after Confirm Import.
- Import preview shows every new inventory template field in a horizontally scrollable table before saving.
- In the Import Inventory modal, the preview table/list has its own scroll area while Cancel and Confirm Import remain outside the scrolling table.
- Files missing required template columns show the template-mismatch message and keep Confirm Import disabled.
- Imports created after this feature can be deleted as a batch. Imports created before this feature can be cleaned through the Admin-only legacy unbatched cleanup row, with the manual-item caveat above.
- Legacy `.xls` import is not implemented and shows a clear unsupported-format message.
- Inventory does not trigger purchase/reorder automation and does not connect to external systems.

Vendors page current behavior:

- `admin` users can access Vendors and use Add/Edit/Close/Reopen/Send.
- `finance_manager` users can access Vendors read-only.
- `it_manager` and `employee` users do not have Vendors navigation access in the current role model; if they reach the page manually, they should see the app's access-denied pattern.
- `Add Vendor` opens a modal form. Each vendor row has an Edit action that opens the same modal in edit mode and updates the existing vendor.
- The Vendors page action row contains local vendor search, a Filter button/dropdown, and Add Vendor on the right.
- Vendor search placeholder is `Search vendors...` and filters by vendor name, contact person, email, phone/contact details, service, and office address.
- Vendor filter options are Status (`All`, `Active`, `Closed`), Service (`All`, `Transport`, `Food`, `Office Supplies`, `IT Services`, `Security`, `Housekeeping`, `Other`), and Billing cycle (`All`, `Monthly`, `Quarterly`, `Half-yearly`, `Yearly`).
- Search and filters are frontend-local and do not change vendor API behavior.
- Vendor Directory is styled to match the reference: rounded card, icon header, subtitle, vendor-count badge, purple-tinted table header, compact rows, and local pagination footer.
- Desktop Vendor Directory columns are Vendor, Contact, Email, Phone, Service, Start, End, Billing, Status, and Actions. Office Address is intentionally omitted from the desktop table but remains in form/mobile detail contexts.
- Pagination shows up to 10 vendors per page with previous/next controls and numbered buttons.
- Vendor Directory row actions are ordered as `Edit`, `Close`/`Reopen`, and `Send`.
- Active vendors show a `Close` action. Clicking Close opens a confirmation dialog with `Are you sure you want to close this vendor?`, plus Close and Cancel actions. The frontend calls `PATCH /api/vendors/{vendor_id}/close`.
- Closing a vendor sets status to `closed`; if the vendor has no end date, the backend sets end date to the current UTC date.
- Closed vendors show a `Reopen` action. Reopening calls `PATCH /api/vendors/{vendor_id}/reopen`, sets status back to `active`, and preserves the historical end date.
- Vendor rows use the backend `vendor.id` as the React key and Close/Reopen identifier. If close/reopen receives a true 404, the UI shows `Vendor could not be found. Please refresh and try again.` as a compact toast.
- `Send` opens a modal titled `Send Email to Vendor`; recipient email and vendor name are read-only, and subject/message are editable.
- `Send Email` calls `POST /api/vendors/{vendor_id}/email`; the backend records `vendor.email.drafted`, queues an `external_vendor_email` approval for Admin approval, and the frontend shows `Vendor email sent to approval queue`.
- Vendor email send is mock/approval-only. It does not connect to or send through any real email provider.
- Unauthorized roles receive the Admin vendor-management permission block.
- Required vendor fields: vendor name, contact person, email, contact details/phone number, office address, service provided, vendor start date, billing amount, and billing cycle. Vendor end date is optional.
- Billing stores both `billing_amount` and `billing_cycle`. The Add/Edit Vendor modal has a number-only billing amount input and a cycle dropdown. The Vendor Directory displays billing as `₹amount / M`, `₹amount / Q`, `₹amount / HY`, or `₹amount / Y`.
- The frontend normalizes billing amount and billing cycle through `frontend/src/vendorBilling.js` before saving and before verifying the refreshed vendor row. This keeps add/edit persistence checks aligned with the directory display helper.
- Billing display examples confirmed by the formatter test are `₹1000 / M`, `₹4322 / Q`, `₹5232 / HY`, and `₹9000 / Y`.
- The frontend refreshes the Vendor Directory after create/update, then verifies the refreshed row includes the saved billing amount and cycle before showing a vendor save success toast. This avoids a false error when the immediate update response is stale but the refreshed vendor list is correct.
- The backend repairs legacy vendor tables that were created before `billing_amount` existed. Vendor create/list/update/get paths call the safe vendor schema migration before reading or writing vendor rows. Existing legacy rows without amounts display as `— / cycle` until edited with a positive amount.
- Vendor billing display formatting lives in `frontend/src/vendorBilling.js` and is covered by `frontend/src/vendorBilling.test.mjs`.
- Service Provided defaults to `Choose`; vendor name typing can auto-select a category for obvious name signals, while unknown names stay unselected and must be chosen manually.
- Vendor start/end date inputs use native calendar controls (`input type="date"`) so users can pick dates from the browser calendar. The frontend keeps ISO `yyyy-mm-dd` form state for create/edit submissions and shows helper text with the selected date formatted as `dd/mm/yyyy`. The end date may be left blank.
- Backend vendor create/update accepts missing, `null`, or empty-string end dates and stores blank end dates as an empty value for display as `—`.
- The frontend keeps vendor form dates in ISO `yyyy-mm-dd` form state for create/edit submissions.
- Vendor directory date display uses `dd/mm/yyyy` for existing and newly created records.
- Vendor directory displays office address; missing office address renders as `—`.
- Service dropdown options: Choose, Transport, Food, Office Supplies, IT Services, Security, Housekeeping, Other.
- Billing dropdown options: Monthly, Quarterly, Half-yearly, Yearly.
- Saved vendors are stored in the local SQLite `vendors` table and displayed in the Vendors directory table.
- Creating a vendor records `vendor.created` in the audit log with vendor name and actor identity.
- Updating a vendor records `vendor.updated` in the audit log with vendor name and actor identity.
- Closing a vendor records `vendor.closed`; reopening a vendor records `vendor.reopened`.

## 13. Important Files and Folders

Repo root:

- `README.md`: setup and product overview
- `PROJECT_CONTEXT.md`: future Codex handoff source of truth
- `.env.example`: safe committed environment template
- `.env`: local-only environment file, ignored by git
- `.gitignore`: ignores `.env`, venvs, DB, node modules, build output

Backend:

- `backend/requirements.txt`: backend dependencies
- `backend/app/main.py`: FastAPI app and API routes
- `backend/app/core/config.py`: environment loading and settings
- `backend/app/data/mock_data.py`: mock vendor, employee, file, calendar, transcript context
- `backend/app/models/schemas.py`: request schemas
- `backend/app/repositories/admin_repository.py`: SQLite schema and data access
- `backend/app/services/agent_planner.py`: mock and OpenAI agent planner
- `backend/app/services/workflow.py`: Vendor Review Meeting workflow
- `backend/app/services/approval_rules.py`: centralized approval rules and request routing logic
- `backend/app/services/policy.py`: safety policy and approval detection
- `backend/app/services/approval_service.py`: approval queue decisions
- `backend/app/services/auth_service.py`: demo auth and role checks
- `backend/app/services/audit_service.py`: audit logging wrapper
- `backend/tests/test_vendor_workflow.py`: backend tests

Frontend:

- `frontend/package.json`: frontend dependencies and scripts
- `frontend/src/App.jsx`: main React app and UI screens
- `frontend/src/api.js`: API client
- `frontend/src/vendorBilling.js`: vendor billing display helper
- `frontend/src/vendorBilling.test.mjs`: no-dependency billing formatter test
- `frontend/src/main.jsx`: React entrypoint
- `frontend/src/styles.css`: dashboard styling
- `frontend/vite.config.js`: Vite config

## 14. How to Run Backend

From a fresh checkout:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If dependencies are already installed:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

## 15. How to Run Frontend

From a fresh checkout:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

The frontend defaults to backend API base:

```text
http://127.0.0.1:8000
```

This can be overridden with `VITE_API_BASE_URL`. This variable is used in frontend code but is not currently documented in `README.md`.

## 16. How to Run Tests

Backend tests from repo root:

```bash
backend/.venv/bin/python -m pytest backend/tests
```

Alternative if the backend venv is activated:

```bash
python -m pytest backend/tests
```

Frontend build:

```bash
cd frontend
npm run build
```

There is no frontend lint script confirmed in `frontend/package.json`.

## 17. Known Limitations

- Authentication is demo-only and stores plain demo passwords in SQLite.
- No production SSO is implemented.
- No real external integrations are implemented.
- Only Vendor Review Meeting has a confirmed end-to-end execution workflow.
- Travel & Calendar is implemented as an internal/mock module with SQLite-backed travel records and calendar events. Some other admin areas remain planning-only; no real external integrations are connected.
- Vendor create/list/edit/close/reopen is implemented, but vendor delete, attachment, renewal, and contract workflows are not implemented.
- Employee own-task scoping is product direction but not confirmed in repo.
- OpenAI planner mode is available, but live behavior requires a real `OPENAI_API_KEY` and network/API availability.
- If OpenAI planning fails, the app falls back to mock planning.
- OpenAI transcript summary behavior is controlled by `USE_OPENAI_AI`, but production readiness is not confirmed in repo.
- CORS allowlist currently includes `5173`, `5174`, `3000`, and localhost equivalents in `backend/app/main.py`.
- Full SQLite migration framework is not implemented; schema is created with `CREATE TABLE IF NOT EXISTS`. Lightweight compatibility repairs exist for `vendors.billing_amount`, `tickets.requester_role`, optional inventory columns, and Travel/Calendar Google placeholder columns.
- Not confirmed in repo: deployment setup, Docker setup, CI pipeline, frontend unit tests, end-to-end browser tests.

## 18. Next Recommended Tasks

Recommended next tasks based on current code and README direction:

1. Add focused frontend tests or browser smoke tests for login, dashboard, vendor creation, approval queue, and Vendor Review Meeting flow.
2. Add real OpenAI planner readiness smoke test that does not expose secrets.
3. Add vendor edit/disable flows or expand workflows beyond Vendor Review Meeting, starting with expense approval or travel approval because safety rules already exist.
4. Improve database migration strategy before adding more tables.
5. Add production-ready auth plan or SSO integration design, but do not implement real SSO until requested.
6. Add clearer frontend error states for backend unavailable and OpenAI fallback mode.
7. Document `VITE_API_BASE_URL` in `README.md` if frontend API host needs to be configurable for demos.
8. Add audit log filters/search in the UI.
9. Add approvals by type views for vendor, expense, travel, and document actions.

## 19. Manager Demo Script

Use this flow for the current main demo:

1. Start backend:

   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Start frontend:

   ```bash
   cd frontend
   npm run dev
   ```

3. Open:

   ```text
   http://127.0.0.1:5173
   ```

4. Log in as admin:

   ```text
   admin@company.com / admin123
   ```

5. Confirm the dashboard shows:

   - Mock AI Mode unless a real `OPENAI_API_KEY` is configured
   - Logged-in user identity
   - Top horizontal navigation
   - Human Ticket Queue
   - Task tracker, meeting notes, vendor follow-ups, expense exceptions, and automation timeline cards

6. Run the default Vendor Review Meeting automation request:

   ```text
   Plan tomorrow's vendor review meeting, remind everyone, prepare files, take notes during the meeting, and follow up on action items.
   ```

7. Confirm the dashboard updates:

   - Meeting is scheduled from mock data
   - Agenda and mock files are attached
   - Internal reminder is generated
   - Meeting notes are generated
   - Decisions are extracted
   - Action items are created
   - Vendor follow-up email is drafted
   - Vendor email appears in Human Ticket Queue
   - Agent classification, risk, and automation level are visible
   - Audit timeline records actions

8. In Human Ticket Queue:

   - Admin can approve vendor follow-up.
   - Finance Manager cannot approve vendor follow-up.
   - IT Manager cannot approve vendor follow-up.
   - Employee user cannot approve vendor follow-up.
   - Vendor email must not be auto-sent before human approval.

9. Optional admin demo:

   - Log in as `admin@company.com / admin123`.
   - Open Settings.
   - Show User Management.
   - Create, edit, enable/disable, or reset password for demo users.

10. Safety talking point:

   - The app automates preparation work.
   - Risky actions are queued for human approval.
   - External vendor communication is never auto-sent.
   - File deletion, payments, travel bookings, contracts, confidential sharing, legal/compliance, emergency/safety, and policy exceptions require approval or human decision.
