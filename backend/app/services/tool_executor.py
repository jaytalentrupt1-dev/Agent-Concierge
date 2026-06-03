from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.admin_repository import AdminRepository


class ToolExecutor:
    """Maps intent + entities → real repository calls.

    current_user is the dict returned by AuthService (id, role, name, email).
    repository is the AdminRepository instance shared with the app.
    """

    def __init__(self, repository: AdminRepository, current_user: dict):
        self.repo = repository
        self.user = current_user

    def execute(self, intent: str, entities: dict) -> dict:
        handlers = {
            # TICKETS
            "create_ticket":        self.create_ticket,
            "ticket_status_update": self.update_ticket,
            "open_tickets":         self.get_tickets,
            "my_tickets":           self.get_my_tickets,
            "recent_tickets":       self.get_recent_tickets,
            "ticket_details":       self.get_ticket_by_id,
            # TASKS
            "create_task":          self.create_task,
            "open_tasks":           self.get_tasks,
            "overdue_tasks":        self.get_overdue_tasks,
            "my_tasks":             self.get_my_tasks,
            # EXPENSES
            "expense_summary":      self.get_expenses,
            "pending_expenses":     self.get_pending_expenses,
            "approve_expense":      self.approve_expense,
            # INVENTORY
            "inventory_summary":    self.get_inventory,
            "low_inventory":        self.get_low_inventory,
            # VENDORS
            "vendor_list":          self.get_vendors,
            "active_vendors":       self.get_vendors,
            "vendor_billing":       self.get_vendor_billing,
            # DASHBOARD
            "dashboard_summary":    self.get_dashboard_summary,
        }
        handler = handlers.get(intent)
        if not handler:
            return {"error": f"No executor for intent: {intent}"}
        try:
            return handler(entities)
        except Exception as e:
            return {"error": str(e)}

    # ── TICKET METHODS ──────────────────────────────────

    def create_ticket(self, e: dict) -> dict:
        ticket_type = e.get("type", "IT")
        assigned_role = "it_manager" if ticket_type == "IT" else "admin"
        assigned_team = "IT Support" if ticket_type == "IT" else "Admin"
        ticket = self.repo.add_ticket({
            "ticket_type":       ticket_type,
            "title":             e.get("title", ""),
            "description":       e.get("description", ""),
            "category":          e.get("category", "General"),
            "priority":          e.get("priority", "Medium"),
            "branch":            e.get("branch", "Pune"),
            "status":            "Open",
            "requester_user_id": self.user.get("id"),
            "requester_name":    self.user.get("name", ""),
            "requester_email":   self.user.get("email", ""),
            "requester_role":    self.user.get("role", ""),
            "assigned_role":     assigned_role,
            "assigned_team":     assigned_team,
            "due_date":          "",
            "approval_required": False,
        })
        return {
            "success":  True,
            "ticket":   ticket,
            "message":  f"Ticket {ticket.get('ticket_id', '')} created successfully.",
        }

    def update_ticket(self, e: dict) -> dict:
        role = self.user.get("role", "")
        if role not in ("admin", "it_manager"):
            return {"error": "Only Admin or IT Manager can update ticket status."}
        ticket = self._find_ticket_by_string_id(e.get("ticket_id", ""))
        if not ticket:
            return {"error": f"Ticket {e.get('ticket_id', '')} not found."}
        status = e.get("status", "")
        updated = self.repo.update_ticket(ticket["id"], status=status)
        return {
            "success": True,
            "ticket":  updated,
            "message": f"Ticket {ticket.get('ticket_id', '')} status updated to {status}.",
        }

    def get_tickets(self, e: dict) -> dict:
        status_filter = e.get("status", "open")
        tickets = [
            t for t in self.repo.list_tickets()
            if t.get("status", "").lower() == status_filter.lower()
        ]
        if self.user.get("role") == "employee":
            uid = self.user.get("id")
            tickets = [t for t in tickets if t.get("requester_user_id") == uid]
        limit = int(e.get("limit", 10))
        return {"tickets": tickets[:limit], "count": len(tickets)}

    def get_my_tickets(self, e: dict) -> dict:
        uid = self.user.get("id")
        email = self.user.get("email", "").lower()
        tickets = [
            t for t in self.repo.list_tickets()
            if t.get("requester_user_id") == uid
            or t.get("requester_email", "").lower() == email
        ]
        limit = int(e.get("limit", 10))
        return {"tickets": tickets[:limit], "count": len(tickets)}

    def get_recent_tickets(self, e: dict) -> dict:
        all_tickets = self.repo.list_tickets()
        if self.user.get("role") == "employee":
            uid = self.user.get("id")
            all_tickets = [t for t in all_tickets if t.get("requester_user_id") == uid]
        limit = int(e.get("limit", 10))
        return {"tickets": all_tickets[:limit], "count": len(all_tickets)}

    def get_ticket_by_id(self, e: dict) -> dict:
        ticket_id_str = e.get("ticket_id", "")
        ticket = self._find_ticket_by_string_id(ticket_id_str)
        if not ticket:
            return {"error": f"Ticket {ticket_id_str} not found."}
        return {"ticket": ticket}

    # ── TASK METHODS ────────────────────────────────────

    def create_task(self, e: dict) -> dict:
        role = self.user.get("role", "")
        if role not in ("admin", "it_manager"):
            return {"error": "Only Admin or IT Manager can create tasks."}
        task = self.repo.add_task({
            "title":              e.get("title", ""),
            "description":        e.get("description", e.get("title", "")),
            "category":           e.get("category", "Admin"),
            "department":         e.get("department", "Admin"),
            "assigned_to":        e.get("assigned_to", self.user.get("name", "")),
            "assigned_role":      e.get("assigned_role", role),
            "priority":           e.get("priority", "Medium"),
            "due_date":           e.get("due_date", ""),
            "created_by_user_id": self.user.get("id"),
            "created_by_name":    self.user.get("name", ""),
            "created_by_email":   self.user.get("email", ""),
            "created_by_role":    role,
            "source":             "conci_ai",
        })
        return {
            "success": True,
            "task":    task,
            "message": f"Task {task.get('task_id', '')} created successfully.",
        }

    def get_tasks(self, e: dict) -> dict:
        status = e.get("status", "Open")
        tasks = self.repo.list_tasks(status=status)
        if self.user.get("role") == "employee":
            uid = self.user.get("id")
            name = self.user.get("name", "").lower()
            tasks = [
                t for t in tasks
                if t.get("assigned_user_id") == uid
                or t.get("assigned_to", "").lower() == name
            ]
        limit = int(e.get("limit", 10))
        return {"tasks": tasks[:limit], "count": len(tasks)}

    def get_overdue_tasks(self, e: dict) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        overdue = [
            t for t in self.repo.list_tasks()
            if t.get("status", "").lower() not in ("completed", "cancelled", "closed")
            and t.get("due_date")
            and str(t.get("due_date", "")) < today
        ]
        if self.user.get("role") == "employee":
            uid = self.user.get("id")
            name = self.user.get("name", "").lower()
            overdue = [
                t for t in overdue
                if t.get("assigned_user_id") == uid
                or t.get("assigned_to", "").lower() == name
            ]
        limit = int(e.get("limit", 10))
        return {"tasks": overdue[:limit], "count": len(overdue)}

    def get_my_tasks(self, e: dict) -> dict:
        uid = self.user.get("id")
        name = self.user.get("name", "").lower()
        tasks = [
            t for t in self.repo.list_tasks()
            if t.get("assigned_user_id") == uid
            or t.get("assigned_to", "").lower() == name
        ]
        limit = int(e.get("limit", 10))
        return {"tasks": tasks[:limit], "count": len(tasks)}

    # ── EXPENSE METHODS ─────────────────────────────────

    def get_expenses(self, e: dict) -> dict:
        expenses = self.repo.list_expenses()
        role = self.user.get("role", "")
        if role == "employee":
            uid = self.user.get("id")
            email = self.user.get("email", "").lower()
            expenses = [
                ex for ex in expenses
                if ex.get("employee_user_id") == uid
                or ex.get("employee_email", "").lower() == email
            ]
        limit = int(e.get("limit", 10))
        return {"expenses": expenses[:limit], "count": len(expenses)}

    def get_pending_expenses(self, e: dict) -> dict:
        if self.user.get("role") not in ("admin", "finance_manager"):
            return {"error": "Permission denied — Finance Manager or Admin only."}
        pending = [
            ex for ex in self.repo.list_expenses()
            if ex.get("status", "").lower() in ("pending approval", "pending_approval")
        ]
        total = sum(float(ex.get("amount", 0)) for ex in pending)
        return {"expenses": pending, "count": len(pending), "total_amount": total}

    def approve_expense(self, e: dict) -> dict:
        if self.user.get("role") not in ("admin", "finance_manager"):
            return {"error": "Only Finance Manager or Admin can approve expenses."}
        expense_id_str = e.get("expense_id", "")
        expense = self.repo.get_expense_by_expense_id(expense_id_str)
        if not expense:
            return {"error": f"Expense {expense_id_str} not found."}
        action = e.get("action", "Approved")
        updated = self.repo.update_expense_status(
            expense["id"], action, self.user.get("name", "")
        )
        return {
            "success": True,
            "expense": updated,
            "message": f"Expense {expense_id_str} {action.lower()} successfully.",
        }

    # ── INVENTORY METHODS ────────────────────────────────

    def get_inventory(self, e: dict) -> dict:
        items = self.repo.list_inventory_items()
        status = e.get("status")
        if status:
            items = [i for i in items if i.get("status", "").lower() == status.lower()]
        limit = int(e.get("limit", 20))
        return {"items": items[:limit], "count": len(items)}

    def get_low_inventory(self, e: dict) -> dict:
        items = self.repo.list_inventory_items()
        low = [
            i for i in items
            if int(i.get("quantity", 0)) <= int(i.get("minimum_stock_level", 0))
        ]
        return {"items": low[:10], "count": len(low), "alert": len(low) > 0}

    # ── VENDOR METHODS ───────────────────────────────────

    def get_vendors(self, e: dict) -> dict:
        if self.user.get("role") == "employee":
            return {"error": "You do not have access to vendor information."}
        vendors = self.repo.list_vendors()
        status = e.get("status", "active")
        if status:
            vendors = [v for v in vendors if v.get("status", "").lower() == status.lower()]
        return {"vendors": vendors, "count": len(vendors)}

    def get_vendor_billing(self, e: dict) -> dict:
        if self.user.get("role") not in ("admin", "finance_manager"):
            return {"error": "Permission denied — Finance Manager or Admin only."}
        vendors = [v for v in self.repo.list_vendors() if v.get("status", "").lower() == "active"]
        total_monthly = sum(
            float(v.get("billing_amount", 0))
            for v in vendors
            if v.get("billing_cycle", "").lower() == "monthly"
        )
        return {"vendors": vendors, "count": len(vendors), "total_monthly_billing": total_monthly}

    # ── DASHBOARD ────────────────────────────────────────

    def get_dashboard_summary(self, e: dict) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        tickets = self.repo.list_tickets()
        tasks = self.repo.list_tasks()
        expenses = self.repo.list_expenses()
        vendors = self.repo.list_vendors()
        items = self.repo.list_inventory_items()
        return {
            "open_tickets":     len([t for t in tickets if t.get("status", "").lower() == "open"]),
            "open_tasks":       len([t for t in tasks if t.get("status", "").lower() == "open"]),
            "overdue_tasks":    len([
                t for t in tasks
                if t.get("status", "").lower() not in ("completed", "cancelled", "closed")
                and t.get("due_date") and str(t.get("due_date", "")) < today
            ]),
            "pending_expenses": len([
                ex for ex in expenses
                if ex.get("status", "").lower() in ("pending approval", "pending_approval")
            ]),
            "active_vendors":   len([v for v in vendors if v.get("status", "").lower() == "active"]),
            "inventory_total":  len(items),
        }

    # ── HELPERS ──────────────────────────────────────────

    def _find_ticket_by_string_id(self, ticket_id_str: str) -> dict | None:
        if not ticket_id_str:
            return None
        needle = str(ticket_id_str).upper()
        for t in self.repo.list_tickets():
            if str(t.get("ticket_id", "")).upper() == needle:
                return t
        return None
