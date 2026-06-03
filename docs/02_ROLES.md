# Roles & Permissions — Agent Admin-IT

---

## Demo Credentials

| Email | Password | Role | Name |
|-------|----------|------|------|
| admin@company.com | admin123 | admin | Admin User |
| it@company.com | it123 | it_manager | IT Manager |
| finance@company.com | finance123 | finance_manager | Finance Manager |
| employee@company.com | employee123 | employee | Employee User |

Demo auth only. Production must replace with SSO, hashed passwords, secure sessions.

---

## Role Capabilities

### `admin`
- Full access to everything
- Manage users, roles, vendors, inventory, all tasks, all tickets, all approvals, all reports
- Only role that can: access Agents dashboard, run/pause agents, manage users, approve vendor emails
- Navigation: Dashboard, Vendors, Tasks, Tickets, Travel & Calendar, Expenses, Inventory, Reports, Agents, Settings

### `it_manager`
- Dashboard, Inventory, Tasks, Tickets, Reports, Settings
- Manage IT tasks, IT tickets, inventory (add/edit/import/delete/status)
- Approve IT support / account / device / password approvals
- Cannot see: Finance data, vendor billing amounts, Expenses, Travel, Agents

### `finance_manager`
- Dashboard, Travel & Calendar, Expenses, Reports, Tasks, Tickets, Vendors, Inventory, Settings
- Manage finance tasks, finance-related Admin tickets
- Approve expense / payment / invoice / reimbursement approvals
- Vendor access: read-only; Inventory access: read-only
- Cannot: manage vendors/inventory, see IT-only data, approve vendor emails

### `employee`
- Dashboard, Tickets, Tasks, Settings (profile + connectors only)
- Create IT and Admin tickets; view own tickets only
- Create task requests; view own/assigned tasks only
- Cannot: approve anything, access Vendors/Inventory/Expenses/Travel/Reports/Agents

---

## Backend Auth Pattern

```python
# In main.py — dependency functions used on routes:

def current_user(token: str = Depends(current_token)) -> dict:
    # validates Bearer token, returns user dict

def admin_user(user: dict = Depends(current_user)) -> dict:
    # raises 403 if role != admin (uses can_manage_users())

# Role helpers from auth_service.py:
can_manage_users(user)    # admin only
can_view_all(user)        # admin only
can_manage_it(user)       # it_manager
can_manage_finance(user)  # finance_manager
can_view_own_only(user)   # employee
```

Manual role check pattern (used where `admin_user` dependency isn't enough):
```python
if user.get("role") != "admin":
    raise HTTPException(status_code=403, detail="Admin access required")
```

---

## Frontend Auth Pattern

- Token stored in `sessionStorage` as `admin_agent_token`
- All API calls via `request()` in `frontend/src/api.js` — adds `Authorization: Bearer <token>` automatically
- `authStorage.js` handles read/write; legacy `localStorage` tokens are cleared on load
- Role-based navigation defined in `frontend/src/navigationConfig.js`
- Deep link auth: URL preserved during login, user returned to requested route after login if role allows

---

## Normalised Role Values (backend)

Always stored/compared as: `admin` · `it_manager` · `finance_manager` · `employee`

Display labels: `Admin` · `IT Manager` · `Finance Manager` · `Employee`

The backend normalises display labels to snake_case on user create/update.
