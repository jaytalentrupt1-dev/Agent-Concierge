from __future__ import annotations

import base64
import binascii
import csv
import io
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from app.core.config import settings
from app.data.mock_data import get_mock_context
from app.models.schemas import (
    ApprovalDecisionRequest,
    CalendarEventRequest,
    ChatbotRequest,
    CommandRequest,
    CommunicationSendRequest,
    ConnectorDisconnectRequest,
    ExpenseCreateRequest,
    ExpenseImportConfirmRequest,
    ExpenseImportPreviewRequest,
    ExpenseStatusUpdateRequest,
    ExpenseUpdateRequest,
    EmailConnectorConfigRequest,
    InventoryBulkDeleteRequest,
    InventoryImportCreateRequest,
    InventoryImportPreviewRequest,
    InventoryItemRequest,
    InventoryStatusUpdateRequest,
    LoginRequest,
    PasswordResetRequest,
    ReportImportRequest,
    RouteRequest,
    TaskRequest,
    TaskStatusUpdateRequest,
    TicketCreateRequest,
    TicketStatusUpdateRequest,
    TicketUpdateRequest,
    TravelRecordRequest,
    UserCreateRequest,
    UserUpdateRequest,
    VendorCreateRequest,
    VendorEmailRequest,
    VendorUpdateRequest,
    WhatsAppConnectorConfigRequest,
)
from app.repositories.admin_repository import AdminRepository
from app.services.agent_planner import get_agent_planner
from app.services.approval_rules import ApprovalRulesService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.communication_service import CommunicationService
from app.services.auth_service import (
    AuthService,
    can_approve_request,
    can_manage_finance,
    can_manage_it,
    can_manage_users,
    can_view_all,
    can_view_own_only,
    public_user,
)
from app.services.inventory_import import parse_tabular_file, preview_inventory_file
from app.services.expense_import import preview_expense_file
from app.services.mock_ai import get_ai_service
from app.services.workflow import VendorReviewWorkflow


def create_app(database_path: str | None = None) -> FastAPI:
    repository = AdminRepository(database_path or settings.database_path)
    repository.init_schema()
    repository.seed_demo_users()
    repository.seed_demo_tasks()
    repository.seed_demo_tickets()
    repository.seed_demo_expenses()
    repository.seed_demo_inventory()
    repository.seed_demo_travel()
    repository.seed_demo_reports()
    repository.seed_message_templates()

    rules = ApprovalRulesService()
    audit = AuditService(repository)
    approvals = ApprovalService(repository, audit, rules)
    auth = AuthService(repository, audit)
    communications = CommunicationService(repository, audit)
    ai = get_ai_service(settings)
    planner = get_agent_planner(settings)
    workflow = VendorReviewWorkflow(
        repository=repository,
        audit=audit,
        approvals=approvals,
        ai=ai,
        planner=planner,
        rules=rules,
    )

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5174",
            "http://localhost:5174",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.repository = repository
    app.state.workflow = workflow
    app.state.approvals = approvals
    app.state.planner = planner
    app.state.auth = auth
    app.state.communications = communications
    app.state.approval_rules = rules

    def current_token(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Login required")
        return authorization.removeprefix("Bearer ").strip()

    def current_user(token: str = Depends(current_token)) -> dict:
        user = auth.user_for_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        return user

    def admin_user(user: dict = Depends(current_user)) -> dict:
        if not can_manage_users(user):
            raise HTTPException(status_code=403, detail="Admin role required")
        return user

    def vendor_viewer_user(user: dict = Depends(current_user)) -> dict:
        if not (can_view_all(user) or can_manage_finance(user)):
            raise HTTPException(status_code=403, detail="Vendor access requires Admin or Finance Manager role")
        return user

    def vendor_manager_user(user: dict = Depends(current_user)) -> dict:
        if not can_view_all(user):
            raise HTTPException(status_code=403, detail="Admin role required")
        return user

    def can_send_communication(user: dict, module: str) -> bool:
        normalized = str(module or "general").strip().lower().replace("_", "-")
        if can_view_all(user):
            return True
        if can_manage_finance(user):
            return normalized in {
                "expense", "expenses", "vendor", "vendors", "vendor-billing",
                "report", "reports", "travel", "calendar", "finance", "settings", "general",
            }
        if can_manage_it(user):
            return normalized in {"ticket", "tickets", "inventory", "it", "task", "tasks", "report", "reports", "settings", "general"}
        if can_view_own_only(user):
            return normalized in {"ticket", "tickets", "task", "tasks", "request", "requests", "settings", "general"}
        return False

    def email_connector_status(provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized == "mock email":
            return "mock_mode"
        if normalized == "smtp" and settings.smtp_host and settings.email_from_address:
            return "connected"
        if normalized == "sendgrid" and settings.sendgrid_api_key and settings.email_from_address:
            return "connected"
        return "mock_mode"

    def whatsapp_connector_status(provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized == "mock whatsapp":
            return "mock_mode"
        if normalized == "twilio whatsapp" and settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from:
            return "connected"
        if normalized == "whatsapp cloud api" and settings.whatsapp_cloud_access_token and settings.whatsapp_phone_number_id:
            return "connected"
        return "mock_mode"

    def inventory_viewer_user(user: dict = Depends(current_user)) -> dict:
        if not (can_view_all(user) or can_manage_it(user) or can_manage_finance(user)):
            raise HTTPException(status_code=403, detail="Inventory access requires Admin, IT Manager, or Finance Manager role")
        return user

    def inventory_manager_user(user: dict = Depends(current_user)) -> dict:
        if not (can_view_all(user) or can_manage_it(user)):
            raise HTTPException(status_code=403, detail="Inventory management requires Admin or IT Manager role")
        return user

    def expense_import_user(user: dict = Depends(current_user)) -> dict:
        if not (can_view_all(user) or can_manage_finance(user)):
            raise HTTPException(status_code=403, detail="Expense import requires Admin or Finance Manager role")
        return user

    def travel_user(user: dict = Depends(current_user)) -> dict:
        if not (can_view_all(user) or can_manage_finance(user)):
            raise HTTPException(status_code=403, detail="Travel & Calendar access requires Admin or Finance Manager role")
        return user

    def can_view_expense(user: dict, expense: dict) -> bool:
        if can_view_all(user) or can_manage_finance(user):
            return True
        if can_view_own_only(user):
            return expense.get("employee_user_id") == user["id"] or expense.get("employee_email") == user["email"]
        if can_manage_it(user):
            return (
                str(expense.get("department", "")).lower() == "it"
                or str(expense.get("category", "")).lower() in {"software", "internet / phone"}
                or expense.get("employee_user_id") == user["id"]
            )
        return False

    def can_manage_expense(user: dict, expense: dict) -> bool:
        if can_view_all(user) or can_manage_finance(user):
            return True
        if can_view_own_only(user):
            return expense.get("employee_user_id") == user["id"] and expense.get("status") in {"Draft", "Needs Info"}
        return False

    def visible_expenses_for(user: dict) -> list[dict]:
        return [expense for expense in repository.list_expenses() if can_view_expense(user, expense)]

    def expense_payload_for_user(payload: ExpenseCreateRequest | ExpenseUpdateRequest, user: dict, existing: dict | None = None) -> dict:
        payload_data = payload.model_dump()
        if can_view_own_only(user):
            payload_data["employee_user_id"] = user["id"]
            payload_data["employee_name"] = user["name"]
            payload_data["employee_email"] = user["email"]
            payload_data["employee_role"] = user["role"]
            if not existing:
                payload_data["status"] = "Pending Approval" if payload_data["approval_required"] else payload_data["status"]
        else:
            employee_email = payload_data.get("employee_email") or user["email"]
            employee_user = repository.get_user_by_email(employee_email)
            payload_data["employee_user_id"] = employee_user.get("id") if employee_user else None
            payload_data["employee_name"] = payload_data.get("employee_name") or (employee_user.get("name") if employee_user else "") or user["name"]
            payload_data["employee_email"] = employee_email or user["email"]
            payload_data["employee_role"] = (employee_user.get("role") if employee_user else "") or user["role"]
        if payload_data["approval_required"] and payload_data["status"] in {"Draft", "Submitted"}:
            payload_data["status"] = "Pending Approval"
        return payload_data

    def ticket_assignment(ticket_type: str, category: str) -> dict:
        category_text = category.lower()
        if ticket_type == "IT":
            return {"assigned_role": "it_manager", "assigned_team": "IT Service Desk"}
        if any(term in category_text for term in ["finance", "invoice", "payment", "expense", "reimbursement"]):
            return {"assigned_role": "finance_manager", "assigned_team": "Finance"}
        return {"assigned_role": "admin", "assigned_team": "Admin"}

    def is_finance_related_ticket(ticket: dict) -> bool:
        category_text = f"{ticket.get('category', '')} {ticket.get('assigned_role', '')}".lower()
        return ticket.get("ticket_type") == "Admin" and any(
            term in category_text for term in ["finance", "invoice", "payment", "expense", "reimbursement"]
        )

    def can_view_ticket(user: dict, ticket: dict) -> bool:
        if can_view_all(user):
            return True
        if can_view_own_only(user):
            return ticket.get("requester_user_id") == user["id"]
        if can_manage_it(user) and ticket.get("ticket_type") == "IT":
            return True
        if can_manage_finance(user) and is_finance_related_ticket(ticket):
            return True
        return False

    def can_manage_ticket(user: dict, ticket: dict) -> bool:
        if can_view_all(user):
            return True
        if can_manage_it(user) and ticket.get("ticket_type") == "IT":
            return True
        if can_manage_finance(user) and is_finance_related_ticket(ticket):
            return True
        return False

    def visible_tickets_for(user: dict) -> list[dict]:
        return [ticket for ticket in repository.list_tickets() if can_view_ticket(user, ticket)]

    def task_assignee_matches(user: dict, task: dict) -> bool:
        if task.get("assigned_user_id") == user.get("id"):
            return True
        assigned_email = str(task.get("assigned_email", "") or task.get("owner_email", "")).strip().lower()
        if assigned_email and assigned_email == str(user.get("email", "")).lower():
            return True
        assigned_to = str(task.get("assigned_to", "")).strip().lower()
        return assigned_to in {str(user.get("email", "")).lower(), str(user.get("name", "")).lower()}

    def assignable_users_for(user: dict) -> list[dict]:
        users = [item for item in auth.list_users() if item.get("enabled", True)]
        role = user.get("role", "")
        if can_view_all(user):
            return users
        if role == "it_manager":
            return [item for item in users if item["id"] == user["id"] or item.get("role") == "it_manager"]
        if role == "finance_manager":
            return [item for item in users if item["id"] == user["id"] or item.get("role") == "finance_manager"]
        if can_view_own_only(user):
            return [item for item in users if item["id"] == user["id"]]
        return [item for item in users if item["id"] == user["id"]]

    def match_assignable_user(payload_data: dict, user: dict) -> dict:
        assignable = assignable_users_for(user)
        by_id = {int(item["id"]): item for item in assignable if item.get("id") is not None}
        assigned_user_id = payload_data.get("assigned_user_id")
        if assigned_user_id:
            try:
                assigned_id = int(assigned_user_id)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="Assigned user is invalid") from None
            assigned = by_id.get(assigned_id)
            if not assigned:
                raise HTTPException(status_code=403, detail="Task assignment not permitted")
            return assigned

        assigned_email = str(payload_data.get("assigned_email", "")).strip().lower()
        assigned_to = str(payload_data.get("assigned_to", "")).strip().lower()
        if assigned_email or assigned_to:
            for item in assignable:
                if assigned_email and str(item.get("email", "")).lower() == assigned_email:
                    return item
                if assigned_to and assigned_to in {
                    str(item.get("email", "")).lower(),
                    str(item.get("name", "")).lower(),
                }:
                    return item
        return {}

    def resolved_task_payload_for_user(payload: TaskRequest, user: dict) -> dict:
        payload_data = payload.model_dump()
        if can_view_own_only(user):
            requested_id = payload_data.get("assigned_user_id")
            requested_email = str(payload_data.get("assigned_email", "")).strip().lower()
            requested_to = str(payload_data.get("assigned_to", "")).strip().lower()
            requested_other = (
                (requested_id and int(requested_id) != int(user["id"]))
                or (requested_email and requested_email != str(user["email"]).lower())
                or (requested_to and requested_to not in {str(user["email"]).lower(), str(user["name"]).lower()})
            )
            if requested_other:
                raise HTTPException(status_code=403, detail="Task assignment not permitted")
            assigned_user = user
        else:
            assigned_user = match_assignable_user(payload_data, user)

        if assigned_user:
            payload_data.update(
                {
                    "assigned_user_id": assigned_user["id"],
                    "assigned_to": assigned_user["name"],
                    "assigned_email": assigned_user["email"],
                    "assigned_role": assigned_user["role"],
                }
            )
        elif not can_view_all(user):
            raise HTTPException(status_code=403, detail="Task assignment not permitted")
        elif not str(payload_data.get("assigned_to", "")).strip():
            raise HTTPException(status_code=422, detail="Assigned user is required")

        if can_view_own_only(user):
            payload_data["source"] = "employee_request"
        else:
            payload_data["source"] = "manual"
        payload_data["owner_name"] = payload_data.get("assigned_to", "")
        payload_data["owner_email"] = payload_data.get("assigned_email", "")
        payload_data["created_by_user_id"] = user["id"]
        payload_data["created_by_name"] = user["name"]
        payload_data["created_by_email"] = user["email"]
        payload_data["created_by_role"] = user["role"]
        return payload_data

    def is_it_related_task(task: dict) -> bool:
        text = " ".join([
            str(task.get("category", "")),
            str(task.get("department", "")),
            str(task.get("assigned_role", "")),
        ]).lower()
        return "it" in text or task.get("assigned_role") == "it_manager"

    def is_finance_related_task(task: dict) -> bool:
        text = " ".join([
            str(task.get("category", "")),
            str(task.get("department", "")),
            str(task.get("assigned_role", "")),
        ]).lower()
        return any(term in text for term in ["finance", "expense", "invoice", "payment"]) or task.get("assigned_role") == "finance_manager"

    def can_view_task(user: dict, task: dict) -> bool:
        if can_view_all(user):
            return True
        created_by_user = task.get("created_by_user_id") == user["id"] or task.get("created_by_email") == user["email"]
        if can_manage_it(user) and (is_it_related_task(task) or created_by_user or task_assignee_matches(user, task)):
            return True
        if can_manage_finance(user) and (is_finance_related_task(task) or created_by_user or task_assignee_matches(user, task)):
            return True
        if can_view_own_only(user):
            return (
                created_by_user
                or task_assignee_matches(user, task)
            )
        return task_assignee_matches(user, task)

    def can_manage_task(user: dict, task: dict) -> bool:
        if can_view_all(user):
            return True
        created_by_user = task.get("created_by_user_id") == user["id"] or task.get("created_by_email") == user["email"]
        if can_manage_it(user) and (is_it_related_task(task) or created_by_user):
            return True
        if can_manage_finance(user) and (is_finance_related_task(task) or created_by_user or task_assignee_matches(user, task)):
            return True
        if can_view_own_only(user):
            return created_by_user
        return False

    def visible_tasks_for(user: dict) -> list[dict]:
        return [task for task in repository.list_tasks() if can_view_task(user, task)]

    def create_task_assignment_notification(task: dict, actor: dict) -> None:
        if not task.get("assigned_user_id"):
            return
        due_text = f" Due: {task['due_date']}." if task.get("due_date") else ""
        repository.add_notification(
            {
                "title": "New task assigned",
                "message": f"New task assigned: {task['title']} Assigned by {actor['name']}.{due_text}",
                "type": "task.assigned",
                "related_entity_type": "task",
                "related_entity_id": task["id"],
                "user_id": task["assigned_user_id"],
                "target_role": "",
            }
        )

    def can_view_notification(user: dict, notification: dict) -> bool:
        if notification.get("related_entity_type") == "ticket":
            related_id = str(notification.get("related_entity_id", ""))
            ticket = repository.get_ticket(int(related_id)) if related_id.isdigit() else {}
            if ticket and not can_view_ticket(user, ticket):
                return False
        if can_view_all(user):
            return True
        if notification.get("user_id") == user["id"]:
            return True
        return notification.get("target_role") == user["role"]

    def serialize_notification(user: dict, notification: dict) -> dict:
        read_user_ids = set(notification.get("read_user_ids", []))
        read = user["id"] in read_user_ids
        return {
            "id": notification["id"],
            "title": notification["title"],
            "message": notification["message"],
            "type": notification["type"],
            "related_entity_type": notification["related_entity_type"],
            "related_entity_id": notification["related_entity_id"],
            "created_at": notification["created_at"],
            "read": read,
            "unread": not read,
            "user_id": notification.get("user_id"),
            "target_role": notification.get("target_role", ""),
        }

    def visible_notifications_for(user: dict) -> list[dict]:
        return [
            serialize_notification(user, notification)
            for notification in repository.list_notifications(limit=100)
            if can_view_notification(user, notification)
        ]

    def create_ticket_notification(ticket: dict, notification_type: str, title: str, message: str) -> None:
        repository.add_notification(
            {
                "title": title,
                "message": message,
                "type": notification_type,
                "related_entity_type": "ticket",
                "related_entity_id": ticket["id"],
                "user_id": ticket.get("requester_user_id"),
                "target_role": ticket.get("assigned_role", ""),
            }
        )

    def create_ticket_status_notification(ticket: dict) -> None:
        if ticket["status"] == "Resolved":
            create_ticket_notification(
                ticket,
                "ticket.resolved",
                "Ticket resolved",
                f"Ticket resolved: {ticket['title']}",
            )
            return
        if ticket["status"] == "Closed":
            create_ticket_notification(
                ticket,
                "ticket.closed",
                "Ticket closed",
                f"Ticket closed: {ticket['title']}",
            )
            return
        create_ticket_notification(
            ticket,
            "ticket.status_changed",
            "Ticket status changed",
            f"Ticket status changed: {ticket['title']} is now {ticket['status']}",
        )

    def visible_approvals_for(user: dict) -> list[dict]:
        approvals_for_user = repository.list_approvals()
        if can_view_all(user):
            return approvals_for_user
        return [approval for approval in approvals_for_user if can_approve_request(user, approval)]

    def month_label(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(str(value or "")[:10])
        except ValueError:
            return "Unknown"
        return parsed.strftime("%b %Y")

    def count_chart(items: list[dict], field: str) -> list[dict]:
        counts: dict[str, int] = {}
        for item in items:
            key = str(item.get(field) or "Unassigned")
            counts[key] = counts.get(key, 0) + 1
        return [{"name": key, "value": counts[key]} for key in sorted(counts)]

    def sum_chart(items: list[dict], group_field: str, value_field: str) -> list[dict]:
        totals: dict[str, float] = {}
        for item in items:
            key = str(item.get(group_field) or "Unassigned")
            totals[key] = totals.get(key, 0) + float(item.get(value_field) or 0)
        return [{"name": key, "value": round(totals[key], 2)} for key in sorted(totals)]

    def monthly_sum_chart(items: list[dict], date_field: str, value_field: str) -> list[dict]:
        totals: dict[str, dict] = {}
        for item in items:
            date_value = str(item.get(date_field) or "")
            label = month_label(date_value)
            sort_key = date_value[:7] if date_value else "9999-99"
            bucket = totals.setdefault(label, {"name": label, "value": 0.0, "sort_key": sort_key})
            bucket["value"] += float(item.get(value_field) or 0)
        return [
            {"name": item["name"], "value": round(item["value"], 2)}
            for item in sorted(totals.values(), key=lambda row: row["sort_key"])
        ]

    def monthly_count_chart(items: list[dict], date_field: str) -> list[dict]:
        counts: dict[str, dict] = {}
        for item in items:
            date_value = str(item.get(date_field) or "")
            label = month_label(date_value)
            sort_key = date_value[:7] if date_value else "9999-99"
            bucket = counts.setdefault(label, {"name": label, "value": 0, "sort_key": sort_key})
            bucket["value"] += 1
        return [
            {"name": item["name"], "value": item["value"]}
            for item in sorted(counts.values(), key=lambda row: row["sort_key"])
        ]

    def vendor_billing_by_month() -> list[dict]:
        return monthly_sum_chart(repository.list_vendors(), "start_date", "billing_amount")

    def current_month_prefix() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def is_current_month(value: str) -> bool:
        return str(value or "").startswith(current_month_prefix())

    def currency_total(items: list[dict], field: str) -> float:
        return round(sum(float(item.get(field) or 0) for item in items), 2)

    def vendor_billing_cycle_months(cycle: str) -> int:
        normalized = str(cycle or "Monthly").strip().lower()
        if normalized == "quarterly":
            return 3
        if normalized in {"half-yearly", "half yearly", "half_yearly", "hy"}:
            return 6
        if normalized == "yearly":
            return 12
        return 1

    def vendor_monthly_equivalent(vendor: dict) -> float:
        amount = float(vendor.get("billing_amount") or 0)
        return round(amount / vendor_billing_cycle_months(vendor.get("billing_cycle")), 2)

    def parse_date(value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(str(value or "")[:10])
        except ValueError:
            return None

    def add_months(year: int, month: int, offset: int) -> tuple[int, int]:
        month_index = (year * 12) + (month - 1) + offset
        return month_index // 12, (month_index % 12) + 1

    def quarter_months(year: int, month: int) -> list[tuple[int, int]]:
        quarter_start = ((month - 1) // 3) * 3 + 1
        return [(year, quarter_start + offset) for offset in range(3)]

    def vendor_due_in_month(vendor: dict, year: int, month: int, now: datetime) -> bool:
        if str(vendor.get("status", "")).lower() != "active":
            return False
        if float(vendor.get("billing_amount") or 0) <= 0:
            return False
        start_date = parse_date(vendor.get("start_date")) or now
        months_since_start = (year - start_date.year) * 12 + (month - start_date.month)
        if months_since_start < 0:
            return False
        return months_since_start % vendor_billing_cycle_months(vendor.get("billing_cycle")) == 0

    def expected_vendor_billing_for_months(vendors: list[dict], months: list[tuple[int, int]], now: datetime) -> float:
        total = 0.0
        for vendor in vendors:
            amount = float(vendor.get("billing_amount") or 0)
            for year, month in months:
                if vendor_due_in_month(vendor, year, month, now):
                    total += amount
        return round(total, 2)

    def vendor_service_bucket(service: str) -> str:
        normalized = str(service or "").strip()
        allowed = {"Food", "Transport", "IT Services", "Office Supplies", "Security", "Other"}
        return normalized if normalized in allowed else "Other"

    def vendor_billing_dashboard_for(user: dict) -> dict | None:
        if can_view_own_only(user):
            return None

        can_view_billing = can_view_all(user) or can_manage_finance(user)
        now = datetime.now(timezone.utc)
        active_vendors = [
            vendor for vendor in repository.list_vendors()
            if str(vendor.get("status", "")).lower() == "active"
        ]
        visible_vendors = active_vendors if can_view_billing else [
            vendor for vendor in active_vendors
            if vendor_service_bucket(vendor.get("service_provided")) == "IT Services"
        ]

        service_order = ["Food", "Transport", "IT Services", "Office Supplies", "Security", "Other"]
        service_summary = [
            {
                "service": service,
                "count": len([
                    vendor for vendor in visible_vendors
                    if vendor_service_bucket(vendor.get("service_provided")) == service
                ]),
            }
            for service in service_order
        ]

        current_vendors = [
            {
                "id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "contact_person": vendor.get("contact_person") if can_view_billing else None,
                "contact_details": vendor.get("contact_details") if can_view_billing else None,
                "service_provided": vendor["service_provided"],
                "billing_amount": int(vendor.get("billing_amount") or 0) if can_view_billing else None,
                "billing_cycle": vendor.get("billing_cycle") if can_view_billing else "",
                "monthly_equivalent": vendor_monthly_equivalent(vendor) if can_view_billing else None,
                "status": vendor.get("status"),
                "start_date": vendor.get("start_date"),
                "end_date": vendor.get("end_date"),
            }
            for vendor in visible_vendors
        ]

        billing_rows = [
            {
                "id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "service_provided": vendor["service_provided"],
                "billing_amount": int(vendor.get("billing_amount") or 0),
                "billing_cycle": vendor.get("billing_cycle"),
                "monthly_equivalent": vendor_monthly_equivalent(vendor),
            }
            for vendor in active_vendors
        ] if can_view_billing else []

        next_month = add_months(now.year, now.month, 1)
        expected_billing = [
            {
                "label": "This month",
                "value": expected_vendor_billing_for_months(active_vendors, [(now.year, now.month)], now) if can_view_billing else None,
            },
            {
                "label": "Next month",
                "value": expected_vendor_billing_for_months(active_vendors, [next_month], now) if can_view_billing else None,
            },
            {
                "label": "Current quarter",
                "value": expected_vendor_billing_for_months(active_vendors, quarter_months(now.year, now.month), now) if can_view_billing else None,
            },
            {
                "label": "Current year",
                "value": expected_vendor_billing_for_months(
                    active_vendors,
                    [(now.year, month) for month in range(1, 13)],
                    now,
                ) if can_view_billing else None,
            },
        ]

        closing_soon = []
        for vendor in visible_vendors:
            end_date = parse_date(vendor.get("end_date"))
            if not end_date:
                continue
            days_until_close = (end_date.date() - now.date()).days
            if 0 <= days_until_close <= 60:
                closing_soon.append({
                    "id": vendor["id"],
                    "vendor_name": vendor["vendor_name"],
                    "contact_person": vendor.get("contact_person") if can_view_billing else None,
                    "contact_details": vendor.get("contact_details") if can_view_billing else None,
                    "service_provided": vendor["service_provided"],
                    "billing_amount": int(vendor.get("billing_amount") or 0) if can_view_billing else None,
                    "billing_cycle": vendor.get("billing_cycle") if can_view_billing else "",
                    "end_date": vendor["end_date"],
                    "days_until_close": days_until_close,
                })

        return {
            "visible": True,
            "can_view_billing": can_view_billing,
            "current_vendors": current_vendors,
            "service_summary": service_summary,
            "current_billing": {
                "total_monthly_equivalent": round(sum(row["monthly_equivalent"] for row in billing_rows), 2),
                "rows": billing_rows,
            },
            "expected_billing": expected_billing,
            "closing_soon": sorted(closing_soon, key=lambda vendor: vendor["days_until_close"]),
        }

    def department_workload(tasks: list[dict], tickets: list[dict]) -> list[dict]:
        counts: dict[str, int] = {}
        for task in tasks:
            key = str(task.get("department") or "Tasks")
            counts[key] = counts.get(key, 0) + 1
        for ticket in tickets:
            key = str(ticket.get("assigned_team") or ticket.get("ticket_type") or "Tickets")
            counts[key] = counts.get(key, 0) + 1
        return [{"name": key, "value": counts[key]} for key in sorted(counts)]

    def low_stock_summary(items: list[dict]) -> list[dict]:
        if not items:
            return []
        low = len([
            item for item in items
            if int(item.get("quantity") or 0) <= int(item.get("minimum_stock_level") or 0)
        ])
        return [
            {"name": "Low stock", "value": low},
            {"name": "Healthy", "value": max(len(items) - low, 0)},
        ]

    def dashboard_chart_payload(chart_id: str, title: str, chart_type: str, data: list[dict], value_kind: str = "count") -> dict:
        return {
            "id": chart_id,
            "title": title,
            "chart_type": chart_type,
            "value_kind": value_kind,
            "data": data,
        }

    def dashboard_charts_for(user: dict) -> list[dict]:
        role = user["role"]
        if role == "employee":
            return []

        tickets = visible_tickets_for(user)
        tasks = visible_tasks_for(user)
        inventory_items = repository.list_inventory_items()
        expenses = visible_expenses_for(user)
        travel_records = repository.list_travel_records() if (can_view_all(user) or can_manage_finance(user)) else []

        if can_view_all(user):
            return [
                dashboard_chart_payload("tickets_by_status", "Tickets by Status", "bar", count_chart(tickets, "status")),
                dashboard_chart_payload("tasks_by_status", "Tasks by Status", "bar", count_chart(tasks, "status")),
                dashboard_chart_payload("expenses_by_month", "Expenses by Month", "line", monthly_sum_chart(expenses, "expense_date", "amount"), "currency"),
                dashboard_chart_payload("inventory_by_status", "Inventory by Status", "pie", count_chart(inventory_items, "status")),
            ]

        if can_manage_it(user):
            it_tickets = [ticket for ticket in tickets if ticket.get("ticket_type") == "IT"]
            return [
                dashboard_chart_payload("it_tickets_by_status", "IT Tickets by Status", "bar", count_chart(it_tickets, "status")),
                dashboard_chart_payload("it_tickets_by_category", "IT Tickets by Category", "pie", count_chart(it_tickets, "category")),
                dashboard_chart_payload("inventory_by_status", "Inventory by Status", "pie", count_chart(inventory_items, "status")),
            ]

        if can_manage_finance(user):
            return [
                dashboard_chart_payload("expenses_by_category", "Expenses by Category", "pie", sum_chart(expenses, "category", "amount"), "currency"),
                dashboard_chart_payload("expenses_by_month", "Expenses by Month", "line", monthly_sum_chart(expenses, "expense_date", "amount"), "currency"),
                dashboard_chart_payload("travel_spend_by_month", "Travel Spend by Month", "line", monthly_sum_chart(travel_records, "travel_start_date", "actual_spend"), "currency"),
                dashboard_chart_payload("vendor_billing", "Vendor Billing", "line", vendor_billing_by_month(), "currency"),
            ]

        return []

    def dashboard_card(card_id: str, label: str, value: int | float, value_kind: str = "count") -> dict:
        return {
            "id": card_id,
            "label": label,
            "value": round(value, 2) if isinstance(value, float) else value,
            "value_kind": value_kind,
        }

    def dashboard_quick_action(action_id: str, label: str, target_tab: str) -> dict:
        return {"id": action_id, "label": label, "target_tab": target_tab}

    def role_dashboard_title(role: str) -> str:
        return {
            "admin": "Admin Command Center",
            "it_manager": "IT Command Center",
            "finance_manager": "Finance Command Center",
            "employee": "My Command Center",
        }.get(role, "Command Center")

    def visible_audit_logs_for(user: dict) -> list[dict]:
        logs = repository.list_audit_logs(limit=100)
        if can_view_all(user):
            return logs
        filtered = []
        for log in logs:
            details = log.get("details") or {}
            searchable = f"{log.get('action', '')} {log.get('actor', '')} {details}".lower()
            if log.get("actor") == user["email"] or details.get("actor_user_id") == user["id"]:
                filtered.append(log)
                continue
            if can_manage_it(user) and any(term in searchable for term in ["it", "ticket", "inventory", "report", "task"]):
                filtered.append(log)
                continue
            if can_manage_finance(user) and any(term in searchable for term in ["finance", "expense", "travel", "vendor", "payment", "invoice", "report", "task"]):
                filtered.append(log)
        return filtered

    def dashboard_payload_for(user: dict) -> dict:
        base = repository.dashboard()
        role = user["role"]
        tickets = visible_tickets_for(user)
        tasks = visible_tasks_for(user)
        approvals_for_user = visible_approvals_for(user)
        pending_approvals = [approval for approval in approvals_for_user if approval.get("status") == "pending"]
        audit_logs = visible_audit_logs_for(user)
        inventory_items = repository.list_inventory_items() if (can_view_all(user) or can_manage_it(user) or can_manage_finance(user)) else []
        vendors = repository.list_vendors() if (can_view_all(user) or can_manage_finance(user)) else []
        expenses = visible_expenses_for(user)
        travel_records = repository.list_travel_records() if (can_view_all(user) or can_manage_finance(user)) else []
        reports = visible_reports_for(user) if not can_view_own_only(user) else visible_reports_for(user)

        open_ticket_count = len([ticket for ticket in tickets if ticket.get("status") not in {"Resolved", "Closed"}])
        open_task_count = len([task for task in tasks if task.get("status") not in {"Completed", "Cancelled"}])
        completed_task_count = len([task for task in tasks if task.get("status") == "Completed"])
        waiting_ticket_count = len([
            ticket for ticket in tickets
            if ticket.get("approval_required") or ticket.get("status") in {"Waiting Approval", "Pending Approval"}
        ])

        if role == "admin":
            summary_cards = [
                dashboard_card("total_tickets", "Total Tickets", len(tickets)),
                dashboard_card("open_tasks", "Open Tasks", open_task_count),
                dashboard_card("active_vendors", "Active Vendors", len([vendor for vendor in vendors if vendor.get("status") == "active"])),
                dashboard_card("inventory_items", "Inventory Items", len(inventory_items)),
                dashboard_card(
                    "monthly_expenses",
                    "Monthly Expenses",
                    currency_total([expense for expense in expenses if is_current_month(expense.get("expense_date", ""))], "amount"),
                    "currency",
                ),
                dashboard_card("pending_approvals", "Pending Approvals", len(pending_approvals)),
            ]
            quick_actions = [
                dashboard_quick_action("create_ticket", "Create Ticket", "approvals"),
                dashboard_quick_action("add_vendor", "Add Vendor", "vendors"),
                dashboard_quick_action("add_inventory_item", "Add Inventory", "inventory"),
                dashboard_quick_action("upload_expense", "Upload Expense", "expenses"),
                dashboard_quick_action("import_report", "Import Report", "reports"),
            ]
        elif role == "it_manager":
            it_tickets = [ticket for ticket in tickets if ticket.get("ticket_type") == "IT"]
            it_tasks = [task for task in tasks if is_it_related_task(task)]
            summary_cards = [
                dashboard_card("open_it_tickets", "Open IT Tickets", len([ticket for ticket in it_tickets if ticket.get("status") not in {"Resolved", "Closed"}])),
                dashboard_card("in_progress_tickets", "In Progress Tickets", len([ticket for ticket in it_tickets if ticket.get("status") == "In Progress"])),
                dashboard_card("resolved_tickets", "Resolved Tickets", len([ticket for ticket in it_tickets if ticket.get("status") in {"Resolved", "Closed"}])),
                dashboard_card("inventory_in_use", "Inventory In Use", len([item for item in inventory_items if item.get("status") == "In Use"])),
                dashboard_card("inventory_extra", "Extra Inventory", len([item for item in inventory_items if item.get("status") == "Extra"])),
                dashboard_card("submitted_to_vendor", "Submitted to Vendor", len([item for item in inventory_items if item.get("status") == "Submitted to Vendor"])),
            ]
            quick_actions = [
                dashboard_quick_action("create_ticket", "Create Ticket", "approvals"),
                dashboard_quick_action("add_inventory_item", "Add Inventory", "inventory"),
                dashboard_quick_action("import_inventory", "Import Inventory", "inventory"),
            ]
            tickets = it_tickets
            tasks = it_tasks
        elif role == "finance_manager":
            finance_tasks = [task for task in tasks if is_finance_related_task(task)]
            pending_expenses = [expense for expense in expenses if expense.get("status") in {"Submitted", "Pending Approval", "Needs Info"}]
            approved_expenses = [expense for expense in expenses if expense.get("status") in {"Approved", "Paid", "Reimbursed"}]
            summary_cards = [
                dashboard_card(
                    "monthly_expenses",
                    "Monthly Expenses",
                    currency_total([expense for expense in expenses if is_current_month(expense.get("expense_date", ""))], "amount"),
                    "currency",
                ),
                dashboard_card("pending_expenses", "Pending Expenses", len(pending_expenses)),
                dashboard_card("approved_expenses", "Approved Expenses", len(approved_expenses)),
                dashboard_card("travel_spend", "Travel Spend", currency_total(travel_records, "actual_spend"), "currency"),
                dashboard_card("vendor_billing_followups", "Vendor Bills", len([vendor for vendor in vendors if float(vendor.get("billing_amount") or 0) > 0])),
                dashboard_card("finance_tasks", "Finance Tasks", len(finance_tasks)),
            ]
            quick_actions = [
                dashboard_quick_action("upload_expense", "Upload Expense", "expenses"),
                dashboard_quick_action("add_travel_record", "Add Travel Record", "travel"),
                dashboard_quick_action("export_report", "Export Report", "reports"),
            ]
            tasks = finance_tasks
        else:
            summary_cards = [
                dashboard_card("my_open_tickets", "My Open Tickets", open_ticket_count),
                dashboard_card("my_tasks", "My Tasks", open_task_count),
                dashboard_card("waiting_approval", "Waiting Approval", waiting_ticket_count),
                dashboard_card("completed_tasks", "Completed Tasks", completed_task_count),
            ]
            quick_actions = [
                dashboard_quick_action("create_ticket", "Create Ticket", "approvals"),
                dashboard_quick_action("create_task_request", "Create Task Request", "tasks"),
            ]

        return {
            **base,
            "role": role,
            "title": role_dashboard_title(role),
            "summary_cards": summary_cards,
            "quick_actions": quick_actions,
            "charts": dashboard_charts_for(user),
            "tickets": tickets[:10],
            "tasks": tasks[:10],
            "pending_approvals": pending_approvals[:10],
            "audit_logs": audit_logs[:10],
            "reports": reports[:10],
            "expenses": expenses[:10],
            "travel_records": travel_records[:10],
            "inventory_items": inventory_items[:10],
            "vendors": vendors[:10],
            "vendor_billing_dashboard": vendor_billing_dashboard_for(user),
            "metrics": {
                **base.get("metrics", {}),
                "open_tasks": open_task_count,
                "pending_approvals": len(pending_approvals),
                "open_tickets": open_ticket_count,
                "inventory_items": len(inventory_items),
                "reports": len(reports),
            },
        }

    CHATBOT_ACCESS_DENIED = "You do not have access to that information."
    CHATBOT_EMPTY_RESPONSE = "I couldn’t find matching data for your access level."
    CHATBOT_STOPWORDS = {
        "a", "about", "all", "an", "and", "answer", "any", "are", "as", "ask", "at", "by", "can", "count",
        "current", "dashboard", "data", "details", "do", "find", "for", "from", "get", "give", "has", "have",
        "help", "how", "i", "in", "info", "information", "is", "it", "list", "me", "monthly", "my", "of",
        "month", "on", "open", "overview", "please", "recent", "show", "summary", "tell", "the", "this", "to",
        "today", "total", "visible", "what", "which", "with", "you",
    }
    CHATBOT_DOMAIN_TERMS = {
        "activity", "approval", "approvals", "asset", "assets", "billing", "calendar", "device", "devices",
        "expense", "expenses", "inventory", "report", "reports", "request", "requests", "spend", "supplier",
        "suppliers", "task", "tasks", "ticket", "tickets", "travel", "trip", "vendor", "vendors",
    }
    CHATBOT_INTENT_PHRASES = {
        "recent_tickets": ["recent tickets", "latest tickets", "new tickets", "show recent tickets", "ticket history"],
        "open_tickets": ["open tickets", "open ticket", "unresolved tickets", "active tickets", "pending tickets"],
        "my_tickets": ["my tickets", "my ticket", "own tickets", "tickets assigned to me"],
        "pending_approvals": ["pending approvals", "panding approvals", "approval queue", "waiting approvals", "pending requests"],
        "open_tasks": ["open tasks", "open task", "open task list", "pending tasks", "active tasks", "incomplete tasks"],
        "my_tasks": ["my tasks", "my task", "tasks assigned to me", "own tasks"],
        "vendor_billing": ["vendor billing", "vendor bills", "vendor payment", "supplier billing", "monthly vendor billing"],
        "active_vendors": ["active vendors", "current vendors", "vendor list", "show vendors", "active suppliers"],
        "inventory_summary": ["inventory summary", "inventory status", "stock summary", "device summary", "asset summary"],
        "expenses_this_month": ["expenses this month", "monthly expenses", "this month expenses", "expense this month"],
        "travel_spend": ["travel spend", "travel spending", "travel expense", "travel cost", "trip spend"],
        "reports": ["reports", "show reports", "report list", "available reports"],
        "help": ["help", "what can you do", "how can you help", "commands", "suggestions"],
    }
    CHATBOT_COMMON_TYPOS = {
        "aproval": "approval",
        "aprovals": "approvals",
        "approvel": "approval",
        "approvels": "approvals",
        "expence": "expense",
        "expences": "expenses",
        "inventry": "inventory",
        "opentask": "open task",
        "opentasks": "open tasks",
        "panding": "pending",
        "recnt": "recent",
        "sho": "show",
        "shoe": "show",
        "shwo": "show",
        "sumary": "summary",
        "summery": "summary",
        "tascks": "tasks",
        "tickts": "tickets",
        "venor": "vendor",
        "vender": "vendor",
        "vendr": "vendor",
    }

    def chatbot_response(
        answer: str,
        bullets: list[str] | None = None,
        source: str = "Agent Concierge data",
        table: dict | None = None,
    ) -> dict:
        cleaned_bullets = [str(item).strip() for item in (bullets or []) if str(item).strip()]
        payload = {
            "answer": answer,
            "message": answer,
            "bullets": cleaned_bullets,
            "source": source,
        }
        if table and table.get("columns") and table.get("rows"):
            payload["table"] = table
        return payload

    def chatbot_denied() -> dict:
        return chatbot_response(CHATBOT_ACCESS_DENIED, source="Access control")

    def chatbot_no_data(source: str) -> dict:
        return chatbot_response(CHATBOT_EMPTY_RESPONSE, source=source)

    def chatbot_empty_message(message: str, source: str) -> dict:
        return chatbot_response(message, source=source)

    def parse_simple_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], dict[str, dict]]:
        boundary_match = re.search(r'boundary="?([^";]+)"?', content_type)
        if not boundary_match:
            raise HTTPException(status_code=400, detail="Could not read the uploaded chat file.")
        boundary = boundary_match.group(1).encode("utf-8")
        fields: dict[str, str] = {}
        files: dict[str, dict] = {}
        for raw_part in body.split(b"--" + boundary):
            part = raw_part.strip(b"\r\n")
            if not part or part == b"--":
                continue
            if part.endswith(b"--"):
                part = part[:-2].strip(b"\r\n")
            if b"\r\n\r\n" not in part:
                continue
            raw_headers, content = part.split(b"\r\n\r\n", 1)
            headers = raw_headers.decode("latin-1", errors="ignore")
            disposition_match = re.search(r"Content-Disposition:\s*form-data;\s*(.+)", headers, re.IGNORECASE)
            if not disposition_match:
                continue
            disposition = disposition_match.group(1)
            name_match = re.search(r'name="([^"]+)"', disposition)
            if not name_match:
                continue
            name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]*)"', disposition)
            content = content.rstrip(b"\r\n")
            if filename_match:
                content_type_match = re.search(r"Content-Type:\s*([^\r\n]+)", headers, re.IGNORECASE)
                files[name] = {
                    "filename": Path(filename_match.group(1)).name,
                    "content": content,
                    "content_type": content_type_match.group(1).strip() if content_type_match else "",
                }
            else:
                fields[name] = content.decode("utf-8", errors="replace").strip()
        return fields, files

    def chatbot_file_header_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").lower())

    def chatbot_row_summary(headers: list[str], row: list[str], limit: int = 6) -> str:
        pairs = []
        for index, header in enumerate(headers[:limit]):
            value = row[index] if index < len(row) else ""
            if str(value).strip():
                pairs.append(f"{header}: {value}")
        return ", ".join(pairs) if pairs else ", ".join(str(value) for value in row[:limit] if str(value).strip())

    def chatbot_file_search_terms(text: str) -> list[str]:
        ignored = {
            "above", "attached", "attachment", "can", "check", "file", "find", "from", "give",
            "item", "list", "look", "read", "record", "row", "search", "show", "summarize",
            "summary", "tell", "this", "vendor", "ticket", "what", "which", "xlsx", "csv", "txt",
        }
        return [term for term in chatbot_query_terms(text) if term not in ignored]

    def chatbot_answer_tabular_file(filename: str, file_type: str, rows: list[list[str]], message: str) -> dict:
        if not rows:
            return chatbot_response("I can see the file, but it appears to be empty.", source="Attached file")
        headers = [str(cell or "").strip() or f"Column {index + 1}" for index, cell in enumerate(rows[0])]
        data_rows = rows[1:] if len(rows) > 1 else []
        normalized_headers = {chatbot_file_header_key(header) for header in headers}
        expected_inventory_headers = ["Employee Name", "Serial No.", "Model No.", "RAM", "Disk", "Location", "Status", "Notes"]
        expected_keys = {chatbot_file_header_key(header) for header in expected_inventory_headers}
        looks_like_inventory = "inventory" in filename.lower() or bool(normalized_headers & expected_keys)
        missing_expected = [
            header for header in expected_inventory_headers
            if chatbot_file_header_key(header) not in normalized_headers
        ] if looks_like_inventory else []
        text = chatbot_normalize_input(message)
        source = f"Attached file · {filename}"

        if "column" in text or "header" in text:
            answer = f"This {file_type.upper()} file has {len(headers)} columns."
            bullets = headers
            if missing_expected:
                answer = f"I can read the file, but it is missing these expected columns: {', '.join(missing_expected)}."
            return chatbot_response(answer, bullets, source=source)

        if chatbot_has_any(text, ["how many rows", "row count", "rows"]):
            return chatbot_response(
                f"This {file_type.upper()} file has {len(data_rows)} data rows.",
                [f"Columns: {', '.join(headers)}"],
                source=source,
            )

        search_terms = chatbot_file_search_terms(text)
        if search_terms and chatbot_has_any(text, ["find", "search", "show", "item", "vendor", "ticket"]):
            matched_rows = []
            for row in data_rows:
                haystack = " ".join(str(cell or "") for cell in row).lower()
                if all(term in haystack for term in search_terms):
                    matched_rows.append(row)
            if not matched_rows:
                return chatbot_response(
                    "I can read the file, but I could not find matching rows for that request.",
                    [f"Search terms: {', '.join(search_terms)}"],
                    source=source,
                )
            return chatbot_response(
                f"I found {len(matched_rows)} matching rows in {filename}.",
                [chatbot_row_summary(headers, row) for row in matched_rows[:6]],
                source=source,
            )

        bullets = [
            f"File type: {file_type.upper()}",
            f"Rows: {len(data_rows)}",
            f"Columns: {', '.join(headers)}",
        ]
        sample_records = [chatbot_row_summary(headers, row) for row in data_rows[:3]]
        if sample_records:
            bullets.append(f"Sample records: {' | '.join(sample_records)}")
        if missing_expected:
            answer = f"I can read the file, but it is missing these expected columns: {', '.join(missing_expected)}."
        else:
            answer = f"Yes, I can read this file. It has {len(data_rows)} rows and these columns: {', '.join(headers)}. What would you like me to check?"
        return chatbot_response(answer, bullets, source=source)

    def chatbot_answer_text_file(filename: str, file_bytes: bytes, message: str) -> dict:
        try:
            text_content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text_content = file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return chatbot_response("I can see the file, but I could not decode this text file.", source=f"Attached file · {filename}")
        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        text = chatbot_normalize_input(message)
        source = f"Attached file · {filename}"
        if chatbot_has_any(text, ["how many rows", "how many lines", "line count", "rows"]):
            return chatbot_response(f"This TXT file has {len(lines)} non-empty lines.", source=source)
        terms = chatbot_file_search_terms(text)
        if terms and chatbot_has_any(text, ["find", "search", "show"]):
            matches = [line for line in lines if all(term in line.lower() for term in terms)]
            return chatbot_response(
                f"I found {len(matches)} matching lines in {filename}." if matches else "I can read the file, but I could not find matching text for that request.",
                matches[:6],
                source=source,
            )
        return chatbot_response(
            f"Yes, I can read this text file. It has {len(lines)} non-empty lines.",
            lines[:6],
            source=source,
        )

    def chatbot_answer_for_file(user: dict, message: str, filename: str, file_bytes: bytes, content_type: str = "") -> dict:
        safe_name = Path(filename or "attached-file").name
        if not file_bytes:
            return chatbot_response("I can see the file, but it appears to be empty.", source=f"Attached file · {safe_name}")
        extension = Path(safe_name).suffix.lower()
        if extension in {".csv", ".xlsx", ".xls"}:
            try:
                rows, file_type = parse_tabular_file(safe_name, base64.b64encode(file_bytes).decode("ascii"))
            except ValueError as exc:
                return chatbot_response(str(exc), source=f"Attached file · {safe_name}")
            return chatbot_answer_tabular_file(safe_name, file_type, rows, message)
        if extension == ".txt" or str(content_type or "").startswith("text/"):
            return chatbot_answer_text_file(safe_name, file_bytes, message)
        if extension == ".pdf" or content_type == "application/pdf":
            return chatbot_response(
                "I can see the file, but PDF reading is not supported yet. Please upload CSV, XLSX, or TXT.",
                source=f"Attached file · {safe_name}",
            )
        return chatbot_response(
            "I can see the file, but this file type is not supported yet. Please upload CSV or XLSX.",
            source=f"Attached file · {safe_name}",
        )

    def chatbot_has_any(text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)

    def chatbot_normalize_input(value: str) -> str:
        text = str(value or "").lower().strip()
        text = re.sub(r"[^a-z0-9@\s._-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        for typo, replacement in CHATBOT_COMMON_TYPOS.items():
            text = re.sub(rf"\b{re.escape(typo)}\b", replacement, text)
        return re.sub(r"\s+", " ", text).strip()

    def chatbot_similarity(left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

    def chatbot_local_intent(text: str) -> str:
        normalized = chatbot_normalize_input(text)
        if not normalized:
            return ""
        if chatbot_casual_response(normalized):
            return "casual"

        best_intent = ""
        best_score = 0.0
        normalized_tokens = set(normalized.split())
        for intent, phrases in CHATBOT_INTENT_PHRASES.items():
            for phrase in phrases:
                normalized_phrase = chatbot_normalize_input(phrase)
                phrase_tokens = set(normalized_phrase.split())
                token_score = (
                    len(normalized_tokens.intersection(phrase_tokens)) / len(phrase_tokens)
                    if phrase_tokens else 0.0
                )
                sequence_score = chatbot_similarity(normalized, normalized_phrase)
                score = max(token_score, sequence_score)
                if normalized_phrase in normalized:
                    score = max(score, 1.0)
                if score > best_score:
                    best_score = score
                    best_intent = intent
        return best_intent if best_score >= 0.68 else ""

    def chatbot_openai_intent(text: str) -> str:
        if not (settings.use_openai_ai and settings.openai_api_key):
            return ""
        try:
            from openai import OpenAI

            allowed = sorted(CHATBOT_INTENT_PHRASES.keys())
            client = OpenAI(api_key=settings.openai_api_key)
            prompt = (
                "Classify this Conci AI user message into one intent. "
                "Return only one of these intent ids, or unknown. "
                f"Intent ids: {', '.join(allowed)}.\n"
                f"Message: {text}"
            )
            response = client.responses.create(model=settings.openai_model, input=prompt)
            intent = str(getattr(response, "output_text", "") or "").strip().lower()
            return intent if intent in CHATBOT_INTENT_PHRASES else ""
        except Exception:
            return ""

    def chatbot_detect_intent(message: str) -> tuple[str, str]:
        normalized = chatbot_normalize_input(message)
        return normalized, chatbot_openai_intent(normalized) or chatbot_local_intent(normalized)

    def chatbot_role_label(role: str) -> str:
        return {
            "admin": "Admin",
            "it_manager": "IT Manager",
            "finance_manager": "Finance Manager",
            "employee": "Employee",
        }.get(role, role.replace("_", " ").title())

    def chatbot_money(value: float | int | str | None) -> str:
        try:
            return f"₹{float(value or 0):,.0f}"
        except (TypeError, ValueError):
            return "₹0"

    def chatbot_date(value: str | None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            return datetime.fromisoformat(text[:10]).strftime("%d/%m/%Y")
        except ValueError:
            return text

    def chatbot_billing_cycle_label(cycle: str | None) -> str:
        normalized = str(cycle or "Monthly").strip().lower()
        if normalized == "quarterly":
            return "Q"
        if normalized in {"half-yearly", "half yearly", "half_yearly", "hy"}:
            return "HY"
        if normalized == "yearly":
            return "Y"
        return "M"

    def chatbot_status_counts(items: list[dict], field: str = "status") -> list[str]:
        counts: dict[str, int] = {}
        for item in items:
            label = str(item.get(field) or "Unknown")
            counts[label] = counts.get(label, 0) + 1
        return [f"{label}: {counts[label]}" for label in sorted(counts)]

    def chatbot_group_sum(items: list[dict], label_field: str, value_field: str, limit: int = 5) -> list[str]:
        totals: dict[str, float] = {}
        for item in items:
            label = str(item.get(label_field) or "Other")
            totals[label] = totals.get(label, 0.0) + float(item.get(value_field) or 0)
        return [
            f"{label}: {chatbot_money(value)}"
            for label, value in sorted(totals.items(), key=lambda pair: pair[1], reverse=True)[:limit]
        ]

    def chatbot_current_month_items(items: list[dict], date_field: str) -> list[dict]:
        prefix = current_month_prefix()
        return [item for item in items if str(item.get(date_field) or "").startswith(prefix)]

    def chatbot_query_terms(text: str) -> list[str]:
        terms = re.findall(r"[a-z0-9@._-]+", text)
        ignored = CHATBOT_STOPWORDS | CHATBOT_DOMAIN_TERMS
        return [term for term in terms if len(term) > 2 and term not in ignored]

    def chatbot_filter_by_terms(items: list[dict], text: str, fields: list[str]) -> list[dict]:
        terms = chatbot_query_terms(text)
        if not terms:
            return items
        filtered = []
        for item in items:
            haystack = " ".join(str(item.get(field) or "") for field in fields).lower()
            if all(term in haystack for term in terms):
                filtered.append(item)
        return filtered

    def chatbot_ticket_bullets(tickets: list[dict], limit: int = 6) -> list[str]:
        bullets = []
        for ticket in tickets[:limit]:
            due = chatbot_date(ticket.get("due_date"))
            due_text = f" - due {due}" if due else ""
            bullets.append(
                f"{ticket.get('ticket_id')}: {ticket.get('title')} - {ticket.get('status')} - {ticket.get('priority')}{due_text}"
            )
        return bullets

    def chatbot_task_bullets(tasks: list[dict], limit: int = 6) -> list[str]:
        bullets = []
        for task in tasks[:limit]:
            due = chatbot_date(task.get("due_date"))
            assigned = task.get("assigned_to") or task.get("assigned_role")
            assigned_text = f" - assigned to {assigned}" if assigned else ""
            due_text = f" - due {due}" if due else ""
            bullets.append(
                f"{task.get('task_id')}: {task.get('title')} - {task.get('status')} - {task.get('priority')}{assigned_text}{due_text}"
            )
        return bullets

    def chatbot_vendor_bullets(vendors: list[dict], include_billing: bool, limit: int = 6) -> list[str]:
        bullets = []
        for vendor in vendors[:limit]:
            billing = ""
            if include_billing:
                billing = f" - {chatbot_money(vendor.get('billing_amount'))} / {chatbot_billing_cycle_label(vendor.get('billing_cycle'))}"
            end_date = chatbot_date(vendor.get("end_date"))
            end_text = f" - ends {end_date}" if end_date else ""
            bullets.append(
                f"{vendor.get('vendor_name')} - {vendor.get('service_provided')} - {vendor.get('status')}{billing}{end_text}"
            )
        return bullets

    def chatbot_first_value(item: dict, fields: list[str]) -> str:
        for field in fields:
            value = item.get(field)
            if value is not None and str(value).strip():
                return str(value).strip()
        return "-"

    def chatbot_vendor_table(vendors: list[dict], include_billing: bool = False, limit: int = 6) -> dict:
        columns = ["Vendor Name", "Service", "Contact", "Phone", "Status"]
        if include_billing:
            columns.insert(4, "Billing")
        if any(vendor.get("end_date") for vendor in vendors[:limit]):
            columns.insert(-1, "End Date")
        rows = []
        for vendor in vendors[:limit]:
            row = {
                "Vendor Name": vendor.get("vendor_name") or "-",
                "Service": vendor.get("service_provided") or "-",
                "Contact": chatbot_first_value(vendor, ["contact_person", "contactPerson", "contact"]),
                "Phone": chatbot_first_value(
                    vendor,
                    ["phone", "contact_details", "contactDetails", "contact_number", "contactNumber"],
                ),
                "Status": str(vendor.get("status") or "").title() or "-",
            }
            if include_billing:
                row["Billing"] = f"{chatbot_money(vendor.get('billing_amount'))} / {chatbot_billing_cycle_label(vendor.get('billing_cycle'))}"
            if "End Date" in columns:
                row["End Date"] = chatbot_date(vendor.get("end_date")) or "-"
            rows.append(row)
        return {"columns": columns, "rows": rows}

    def chatbot_vendor_billing_bullets(rows: list[dict], limit: int = 6) -> list[str]:
        return [
            (
                f"{row.get('vendor_name')} - {row.get('service_provided')} - "
                f"{chatbot_money(row.get('billing_amount'))} / {chatbot_billing_cycle_label(row.get('billing_cycle'))} "
                f"(monthly equivalent {chatbot_money(row.get('monthly_equivalent'))})"
            )
            for row in rows[:limit]
        ]

    def chatbot_vendor_billing_table(rows: list[dict], limit: int = 6) -> dict:
        return {
            "columns": ["Vendor", "Cycle Billing", "Monthly Eq."],
            "rows": [
                {
                    "Vendor": row.get("vendor_name") or "-",
                    "Cycle Billing": f"{chatbot_money(row.get('billing_amount'))} / {chatbot_billing_cycle_label(row.get('billing_cycle'))}",
                    "Monthly Eq.": chatbot_money(row.get("monthly_equivalent")),
                }
                for row in rows[:limit]
            ],
        }

    def chatbot_inventory_bullets(items: list[dict], limit: int = 6) -> list[str]:
        bullets = []
        for item in items[:limit]:
            employee = item.get("employee_name") or item.get("assigned_to") or item.get("item_name") or "Inventory item"
            serial = item.get("serial_no") or item.get("serial_number") or "No serial"
            model = item.get("model_no") or item.get("model") or "No model"
            bullets.append(f"{employee} - {serial} - {model} - {item.get('status')} - {item.get('location')}")
        return bullets

    def chatbot_expense_bullets(expenses: list[dict], limit: int = 6) -> list[str]:
        return [
            (
                f"{expense.get('expense_id')}: {expense.get('category')} - {chatbot_money(expense.get('amount'))} "
                f"- {expense.get('status')} - {chatbot_date(expense.get('expense_date'))}"
            )
            for expense in expenses[:limit]
        ]

    def chatbot_travel_bullets(records: list[dict], limit: int = 6) -> list[str]:
        return [
            (
                f"{record.get('travel_id')}: {record.get('employee_name')} - {record.get('destination_from')} to "
                f"{record.get('destination_to')} - {record.get('approval_status')} - {chatbot_money(record.get('actual_spend'))}"
            )
            for record in records[:limit]
        ]

    def chatbot_calendar_bullets(events: list[dict], limit: int = 6) -> list[str]:
        return [
            (
                f"{event.get('event_id')}: {event.get('title')} - {event.get('event_type')} - "
                f"{chatbot_date(event.get('start_datetime'))}"
            )
            for event in events[:limit]
        ]

    def chatbot_report_bullets(reports: list[dict], limit: int = 6) -> list[str]:
        return [
            f"{report.get('report_id')}: {report.get('report_name')} - {report.get('department')} - {report.get('status')}"
            for report in reports[:limit]
        ]

    def chatbot_approval_bullets(approvals: list[dict], limit: int = 6) -> list[str]:
        return [
            (
                f"{approval.get('subject')} - {approval.get('approval_type')} - "
                f"Requested by {approval.get('recipient_name') or approval.get('recipient_email') or 'Unknown'} - "
                f"{str(approval.get('priority') or 'normal').title()} - {chatbot_date(approval.get('created_at'))}"
            )
            for approval in approvals[:limit]
        ]

    def chatbot_activity_bullets(logs: list[dict], limit: int = 6) -> list[str]:
        return [
            f"{log.get('action')} - {log.get('status')} - {log.get('actor')} - {chatbot_date(log.get('created_at'))}"
            for log in logs[:limit]
        ]

    def chatbot_waiting_requests_for(tickets: list[dict], tasks: list[dict]) -> list[str]:
        waiting_tickets = [
            ticket for ticket in tickets
            if ticket.get("approval_required") or ticket.get("status") in {"Waiting Approval", "Pending Approval"}
        ]
        waiting_tasks = [task for task in tasks if task.get("status") == "Waiting Approval"]
        return chatbot_ticket_bullets(waiting_tickets, 5) + chatbot_task_bullets(waiting_tasks, 5)

    def chatbot_overdue_tasks(tasks: list[dict]) -> list[dict]:
        today = datetime.now(timezone.utc).date()
        overdue = []
        for task in tasks:
            due_date = parse_date(task.get("due_date"))
            if due_date and due_date.date() < today and task.get("status") not in {"Completed", "Cancelled"}:
                overdue.append(task)
        return overdue

    def chatbot_select_tickets(tickets: list[dict], text: str) -> list[dict]:
        selected = tickets
        if chatbot_has_any(text, ["waiting", "approval", "pending"]):
            selected = [
                ticket for ticket in selected
                if ticket.get("approval_required") or ticket.get("status") in {"Waiting Approval", "Pending Approval"}
            ]
        elif "resolved" in text:
            selected = [ticket for ticket in selected if ticket.get("status") == "Resolved"]
        elif "closed" in text:
            selected = [ticket for ticket in selected if ticket.get("status") == "Closed"]
        elif "open" in text:
            selected = [ticket for ticket in selected if ticket.get("status") not in {"Resolved", "Closed"}]
        if "critical" in text:
            selected = [ticket for ticket in selected if ticket.get("priority") == "Critical"]
        elif "high" in text:
            selected = [ticket for ticket in selected if ticket.get("priority") == "High"]
        return chatbot_filter_by_terms(selected, text, ["ticket_id", "title", "category", "requester_name", "assigned_team", "status", "priority"])

    def chatbot_select_tasks(tasks: list[dict], text: str) -> list[dict]:
        selected = tasks
        if "overdue" in text:
            selected = chatbot_overdue_tasks(selected)
        elif "completed" in text:
            selected = [task for task in selected if task.get("status") == "Completed"]
        elif "progress" in text:
            selected = [task for task in selected if task.get("status") == "In Progress"]
        elif chatbot_has_any(text, ["waiting", "approval", "pending"]):
            selected = [task for task in selected if task.get("status") == "Waiting Approval"]
        elif "open" in text:
            selected = [task for task in selected if task.get("status") not in {"Completed", "Cancelled"}]
        if "critical" in text:
            selected = [task for task in selected if task.get("priority") == "Critical"]
        elif "high" in text:
            selected = [task for task in selected if task.get("priority") == "High"]
        return chatbot_filter_by_terms(selected, text, ["task_id", "title", "description", "department", "assigned_to", "assigned_role", "created_by_name", "status", "priority"])

    def chatbot_select_inventory(items: list[dict], text: str) -> list[dict]:
        selected = items
        if "submitted" in text and "vendor" in text:
            selected = [item for item in selected if item.get("status") == "Submitted to Vendor"]
        elif "extra" in text:
            selected = [item for item in selected if item.get("status") == "Extra"]
        elif chatbot_has_any(text, ["in use", "use"]):
            selected = [item for item in selected if item.get("status") == "In Use"]
        return chatbot_filter_by_terms(
            selected,
            text,
            ["employee_name", "assigned_to", "item_name", "serial_no", "serial_number", "model_no", "model", "ram", "disk", "location", "status", "notes"],
        )

    def chatbot_select_expenses(expenses: list[dict], text: str) -> list[dict]:
        selected = chatbot_current_month_items(expenses, "expense_date") if chatbot_has_any(text, ["month", "monthly", "this month"]) else expenses
        if chatbot_has_any(text, ["pending", "approval", "needs info"]):
            selected = [expense for expense in selected if expense.get("status") in {"Submitted", "Pending Approval", "Needs Info"}]
        elif "approved" in text:
            selected = [expense for expense in selected if expense.get("status") == "Approved"]
        elif "paid" in text:
            selected = [expense for expense in selected if expense.get("status") in {"Paid", "Reimbursed"}]
        return chatbot_filter_by_terms(selected, text, ["expense_id", "employee_name", "department", "category", "vendor_or_merchant", "status"])

    def chatbot_select_travel(records: list[dict], text: str) -> list[dict]:
        selected = records
        if chatbot_has_any(text, ["upcoming", "pending", "approved", "booked"]):
            selected = [record for record in selected if record.get("approval_status") in {"Approved", "Booked", "Pending Approval"}]
        elif "completed" in text:
            selected = [record for record in selected if record.get("approval_status") == "Completed"]
        return chatbot_filter_by_terms(selected, text, ["travel_id", "employee_name", "department", "destination_from", "destination_to", "purpose", "approval_status"])

    def chatbot_openai_refine(question: str, response: dict) -> dict | None:
        if not (settings.use_openai_ai and settings.openai_api_key):
            return None
        if response.get("answer") in {CHATBOT_ACCESS_DENIED, CHATBOT_EMPTY_RESPONSE}:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            prompt = (
                "Rewrite this Conci AI assistant response for clarity. "
                "Use only the supplied answer and bullets. Do not add facts. "
                "Return strict JSON with keys answer and bullets.\n\n"
                f"Question: {question}\n"
                f"Answer: {response.get('answer')}\n"
                f"Bullets: {json.dumps(response.get('bullets', []))}"
            )
            openai_response = client.responses.create(model=settings.openai_model, input=prompt)
            text = str(getattr(openai_response, "output_text", "") or "").strip()
            parsed = json.loads(text)
            answer = str(parsed.get("answer") or response.get("answer") or "").strip()
            bullets = parsed.get("bullets") if isinstance(parsed.get("bullets"), list) else response.get("bullets", [])
            return chatbot_response(
                answer,
                [str(item) for item in bullets],
                source=f"{response.get('source', 'Agent Concierge data')} · OpenAI",
                table=response.get("table"),
            )
        except Exception:
            return None

    def chatbot_casual_response(text: str) -> dict | None:
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = set(normalized.split())
        if not normalized:
            return None
        if (
            re.search(r"\bare\s+you\s+(male|female)\b", normalized)
            or re.search(r"\bwhat\s+is\s+your\s+gender\b", normalized)
            or "your gender" in normalized
        ):
            return chatbot_response(
                "I don’t have a gender. I’m Conci AI, your digital concierge assistant.",
                source="Conci AI",
            )
        if re.search(r"\bare\s+you\s+(a\s+)?(boy|girl)\b", normalized):
            return chatbot_response(
                "Neither. I’m Conci AI, an AI assistant here to help with your work.",
                source="Conci AI",
            )
        if re.search(r"\bare\s+you\s+human\b", normalized):
            return chatbot_response(
                "No, I’m an AI assistant. I can help you with tickets, tasks, vendors, inventory, expenses, reports, and approvals.",
                source="Conci AI",
            )
        if re.search(r"\bare\s+you\s+real\b", normalized):
            return chatbot_response(
                "I’m real as software, but I’m not a person. I’m here to help you get work done.",
                source="Conci AI",
            )
        if re.search(r"\bwho\s+(made|created|built)\s+you\b", normalized):
            return chatbot_response(
                "I’m Conci AI, built into Agent Concierge to help with admin, IT, finance, and employee workflows.",
                source="Conci AI",
            )
        if re.search(r"\b(what is|whats|what s)\s+your\s+name\b", normalized) or "your name" in normalized:
            return chatbot_response(
                "I’m Conci AI, your assistant for admin, IT, finance, and employee workflows.",
                source="Conci AI",
            )
        if re.search(r"\bwho\s+are\s+you\b", normalized):
            return chatbot_response(
                "I’m Conci AI, your smart concierge for tickets, tasks, vendors, inventory, expenses, reports, and approvals.",
                source="Conci AI",
            )
        if normalized in {"hi", "hello", "hey", "hiya"} or tokens.intersection({"hi", "hello", "hey"}) and len(tokens) <= 4:
            return chatbot_response("Hi! How can I help you today?", source="Conci AI")
        if re.search(r"\bhow\s+are\s+you\b", normalized):
            return chatbot_response("I’m doing well and ready to help.", source="Conci AI")
        if re.search(r"\bwhat\s+can\s+you\s+do\b", normalized) or re.search(r"\bhow\s+can\s+you\s+help\b", normalized):
            return chatbot_response(
                "I can help you check tickets, tasks, vendors, inventory, expenses, travel, reports, approvals, and dashboard summaries based on your access.",
                source="Conci AI",
            )
        if normalized in {"thanks", "thank you", "thank u"} or re.search(r"\b(thanks|thank you|thank u)\b", normalized):
            return chatbot_response("You’re welcome.", source="Conci AI")
        return None

    def chatbot_answer_for(user: dict, message: str) -> dict:
        role = user["role"]
        raw_text = message.strip().lower()
        if not raw_text:
            return chatbot_no_data("Conci AI")

        casual_response = chatbot_casual_response(raw_text)
        if casual_response:
            return casual_response
        text, detected_intent = chatbot_detect_intent(raw_text)

        tickets = visible_tickets_for(user)
        tasks = visible_tasks_for(user)
        approvals_for_user = visible_approvals_for(user)
        audit_logs = visible_audit_logs_for(user)
        reports = visible_reports_for(user)
        dashboard_payload = dashboard_payload_for(user)
        can_view_inventory = can_view_all(user) or can_manage_it(user) or can_manage_finance(user)
        inventory_items = repository.list_inventory_items() if can_view_inventory else []
        can_view_finance = can_view_all(user) or can_manage_finance(user)
        expenses = visible_expenses_for(user) if can_view_finance else []
        travel_records = repository.list_travel_records() if can_view_finance else []
        calendar_events = repository.list_calendar_events() if can_view_finance else []
        vendor_dashboard = vendor_billing_dashboard_for(user)

        if detected_intent == "help":
            return chatbot_response(
                "I can help you check tickets, tasks, vendors, inventory, expenses, travel, reports, approvals, and dashboard summaries based on your access.",
                source="Conci AI",
            )

        asks_user_data = chatbot_has_any(text, ["user", "users", "setting", "settings", "account", "role"])
        asks_vendor = detected_intent in {"vendor_billing", "active_vendors"} or chatbot_has_any(text, ["vendor", "vendors", "supplier", "suppliers", "billing", "bill"])
        asks_expense = detected_intent == "expenses_this_month" or chatbot_has_any(text, ["expense", "expenses", "spend", "reimbursement", "receipt", "merchant"])
        asks_travel = detected_intent == "travel_spend" or chatbot_has_any(text, ["travel", "trip", "calendar", "event"])
        asks_ticket = detected_intent in {"recent_tickets", "open_tickets", "my_tickets"} or chatbot_has_any(text, ["ticket", "tickets"])
        asks_task = detected_intent in {"open_tasks", "my_tasks"} or chatbot_has_any(text, ["task", "tasks"])
        asks_inventory = detected_intent == "inventory_summary" or chatbot_has_any(text, ["inventory", "stock", "device", "devices", "asset", "assets", "laptop"])
        asks_report = detected_intent == "reports" or chatbot_has_any(text, ["report", "reports"])
        asks_approval = detected_intent == "pending_approvals" or chatbot_has_any(text, ["approval", "approvals", "pending request", "pending requests", "waiting"])
        asks_activity = chatbot_has_any(text, ["activity", "audit", "recent"])
        asks_dashboard = detected_intent == "help" or chatbot_has_any(text, ["dashboard", "summary", "overview"])
        explicit_it = chatbot_has_any(text, ["it ticket", "it task", "it report", "it approval", "it dashboard"])
        explicit_finance = chatbot_has_any(text, ["finance ticket", "finance task", "finance report", "finance approval", "finance dashboard"])

        response: dict
        if asks_user_data:
            if not can_view_all(user):
                response = chatbot_denied()
            else:
                users_for_admin = [item for item in auth.list_users() if not item.get("is_demo")]
                if not users_for_admin:
                    response = chatbot_no_data("Users")
                else:
                    response = chatbot_response(
                        f"{len(users_for_admin)} admin-created users are available in User Management.",
                        [f"{item.get('email')} - {item.get('name')} - {chatbot_role_label(item.get('role', ''))}" for item in users_for_admin[:8]],
                        source="Users",
                    )

        elif asks_vendor:
            if not can_view_finance:
                response = chatbot_denied()
            else:
                vendors = vendor_dashboard.get("current_vendors", []) if vendor_dashboard else []
                billing_rows = vendor_dashboard.get("current_billing", {}).get("rows", []) if vendor_dashboard else []
                expected_rows = vendor_dashboard.get("expected_billing", []) if vendor_dashboard else []
                if "highest" in text and billing_rows:
                    highest = sorted(billing_rows, key=lambda row: float(row.get("monthly_equivalent") or 0), reverse=True)[0]
                    response = chatbot_response(
                        f"{highest.get('vendor_name')} has the highest monthly equivalent billing at {chatbot_money(highest.get('monthly_equivalent'))}.",
                        chatbot_vendor_billing_bullets([highest], 1),
                        source="Vendor billing",
                        table=chatbot_vendor_billing_table([highest], 1),
                    )
                elif "expected" in text or chatbot_has_any(text, ["this month", "next month", "quarter", "year"]):
                    if not expected_rows:
                        response = chatbot_empty_message("No vendors found for that request.", "Expected vendor billing")
                    else:
                        response = chatbot_response(
                            "Expected vendor billing is calculated from active vendor billing cycles.",
                            [f"{row.get('label')}: {chatbot_money(row.get('value'))}" for row in expected_rows],
                            source="Expected vendor billing",
                            table={
                                "columns": ["Period", "Expected Billing"],
                                "rows": [
                                    {"Period": row.get("label") or "-", "Expected Billing": chatbot_money(row.get("value"))}
                                    for row in expected_rows
                                ],
                            },
                        )
                elif chatbot_has_any(text, ["billing", "bill"]):
                    total = vendor_dashboard.get("current_billing", {}).get("total_monthly_equivalent", 0) if vendor_dashboard else 0
                    response = chatbot_response(
                        f"Total current monthly equivalent vendor billing is {chatbot_money(total)}.",
                        chatbot_vendor_billing_bullets(billing_rows, 6),
                        source="Vendor billing",
                        table=chatbot_vendor_billing_table(billing_rows, 6),
                    ) if billing_rows else chatbot_empty_message("No vendors found for that request.", "Vendor billing")
                elif "closing" in text:
                    closing = vendor_dashboard.get("closing_soon", []) if vendor_dashboard else []
                    response = chatbot_response(
                        f"{len(closing)} vendors are closing in the next 60 days.",
                        chatbot_vendor_bullets(closing, include_billing=False, limit=6),
                        source="Vendors closing soon",
                        table=chatbot_vendor_table(closing, include_billing=True, limit=6),
                    ) if closing else chatbot_empty_message("No vendors found for that request.", "Vendors closing soon")
                else:
                    selected_vendors = chatbot_filter_by_terms(vendors, text, ["vendor_name", "service_provided", "status"])
                    response = chatbot_response(
                        f"{len(selected_vendors)} active vendors match your access level.",
                        chatbot_vendor_bullets(selected_vendors, include_billing=True, limit=6),
                        source="Vendors",
                        table=chatbot_vendor_table(selected_vendors, include_billing=True, limit=6),
                    ) if selected_vendors else chatbot_empty_message("No vendors found for that request.", "Vendors")

        elif asks_expense:
            if not can_view_finance:
                response = chatbot_denied()
            else:
                selected_expenses = chatbot_select_expenses(expenses, text)
                if not selected_expenses:
                    response = chatbot_empty_message("No expenses found for that request.", "Expenses")
                else:
                    total = currency_total(selected_expenses, "amount")
                    pending = len([expense for expense in selected_expenses if expense.get("status") in {"Submitted", "Pending Approval", "Needs Info"}])
                    timeframe = "this month" if chatbot_has_any(text, ["month", "monthly", "this month"]) else "visible"
                    response = chatbot_response(
                        f"{timeframe.title()} expenses total {chatbot_money(total)}; {pending} need attention.",
                        chatbot_group_sum(selected_expenses, "category", "amount", 5) or chatbot_expense_bullets(selected_expenses, 5),
                        source="Expenses",
                    )

        elif asks_travel:
            if not can_view_finance:
                response = chatbot_denied()
            elif "calendar" in text or "event" in text:
                selected_events = chatbot_filter_by_terms(calendar_events, text, ["event_id", "title", "event_type", "location", "attendees", "status"])
                response = chatbot_response(
                    f"{len(selected_events)} calendar events match your access level.",
                    chatbot_calendar_bullets(selected_events, 6),
                    source="Calendar events",
                ) if selected_events else chatbot_no_data("Calendar events")
            else:
                selected_travel = chatbot_select_travel(travel_records, text)
                if not selected_travel:
                    response = chatbot_no_data("Travel")
                else:
                    total_spend = currency_total(selected_travel, "actual_spend")
                    response = chatbot_response(
                        f"{len(selected_travel)} travel records match your access level with total spend {chatbot_money(total_spend)}.",
                        chatbot_travel_bullets(selected_travel, 6),
                        source="Travel",
                    )

        elif asks_ticket:
            if explicit_it and not (can_view_all(user) or can_manage_it(user)):
                response = chatbot_denied()
            elif explicit_finance and not (can_view_all(user) or can_manage_finance(user)):
                response = chatbot_denied()
            else:
                if detected_intent == "my_tickets":
                    selected_tickets = [ticket for ticket in tickets if ticket.get("requester_user_id") == user["id"]]
                else:
                    selected_tickets = chatbot_select_tickets(tickets, text)
                if not selected_tickets:
                    response = chatbot_empty_message("You don’t have any open tickets right now.", "Tickets")
                elif detected_intent == "recent_tickets":
                    response = chatbot_response(
                        "Here are recent tickets:",
                        chatbot_ticket_bullets(selected_tickets, 6),
                        source="Tickets",
                    )
                elif detected_intent == "my_tickets":
                    response = chatbot_response(
                        "Here are your tickets:",
                        chatbot_ticket_bullets(selected_tickets, 6),
                        source="Tickets",
                    )
                else:
                    open_tickets = [ticket for ticket in selected_tickets if ticket.get("status") not in {"Resolved", "Closed"}]
                    owner = "your" if can_view_own_only(user) else "visible"
                    response = chatbot_response(
                        f"{len(open_tickets)} open {owner} tickets; {len(selected_tickets)} tickets match your question.",
                        chatbot_ticket_bullets(selected_tickets, 6),
                        source="Tickets",
                    )

        elif asks_task:
            if explicit_it and not (can_view_all(user) or can_manage_it(user)):
                response = chatbot_denied()
            elif explicit_finance and not (can_view_all(user) or can_manage_finance(user)):
                response = chatbot_denied()
            else:
                if detected_intent == "my_tasks":
                    selected_tasks = [task for task in tasks if task_assignee_matches(user, task) or task.get("created_by_user_id") == user["id"]]
                else:
                    selected_tasks = chatbot_select_tasks(tasks, text)
                if not selected_tasks:
                    response = chatbot_empty_message("You don’t have any open tasks right now.", "Tasks")
                elif detected_intent == "my_tasks":
                    response = chatbot_response(
                        "Here are your tasks:",
                        chatbot_task_bullets(selected_tasks, 6),
                        source="Tasks",
                    )
                else:
                    open_tasks = [task for task in selected_tasks if task.get("status") not in {"Completed", "Cancelled"}]
                    owner = "your" if can_view_own_only(user) else "visible"
                    response = chatbot_response(
                        f"{len(open_tasks)} open {owner} tasks; {len(selected_tasks)} tasks match your question.",
                        chatbot_task_bullets(selected_tasks, 6),
                        source="Tasks",
                    )

        elif asks_inventory:
            if not can_view_inventory:
                response = chatbot_denied()
            else:
                selected_inventory = chatbot_select_inventory(inventory_items, text)
                if not selected_inventory:
                    response = chatbot_empty_message("No inventory items found for that request.", "Inventory")
                else:
                    response = chatbot_response(
                        f"{len(selected_inventory)} inventory items match your question.",
                        chatbot_status_counts(selected_inventory) + chatbot_inventory_bullets(selected_inventory, 6),
                        source="Inventory",
                    )

        elif asks_report:
            if can_view_own_only(user):
                response = chatbot_denied()
            else:
                selected_reports = chatbot_filter_by_terms(reports, text, ["report_id", "report_name", "report_type", "department", "uploaded_by", "status"])
                response = chatbot_response(
                    f"{len(selected_reports)} reports are visible for your role.",
                    chatbot_report_bullets(selected_reports, 6),
                    source="Reports",
                ) if selected_reports else chatbot_no_data("Reports")

        elif asks_approval:
            if not (can_view_all(user) or can_manage_it(user) or can_manage_finance(user) or can_view_own_only(user)):
                response = chatbot_response("You do not have access to approval data.", source="Approvals")
            elif can_view_own_only(user):
                waiting = chatbot_waiting_requests_for(tickets, tasks)
                response = chatbot_response(
                    "Here are your pending approvals:",
                    waiting,
                    source="My requests",
                ) if waiting else chatbot_empty_message("You don’t have any pending approvals right now.", "My requests")
            else:
                pending_approvals = [approval for approval in approvals_for_user if approval.get("status") == "pending"]
                response = chatbot_response(
                    "Here are your pending approvals:",
                    chatbot_approval_bullets(pending_approvals, 6),
                    source="Approvals",
                ) if pending_approvals else chatbot_empty_message("You don’t have any pending approvals right now.", "Approvals")

        elif asks_activity:
            response = chatbot_response(
                f"{len(audit_logs)} recent activity entries are visible for your role.",
                chatbot_activity_bullets(audit_logs, 6),
                source="Recent activity",
            ) if audit_logs else chatbot_no_data("Recent activity")

        elif asks_dashboard:
            cards = dashboard_payload.get("summary_cards", [])
            response = chatbot_response(
                f"Here is your {chatbot_role_label(role)} dashboard summary.",
                [
                    f"{card['label']}: {chatbot_money(card['value']) if card.get('value_kind') == 'currency' else card['value']}"
                    for card in cards
                ],
                source="Dashboard summary",
            ) if cards else chatbot_no_data("Dashboard summary")

        else:
            response = chatbot_response(
                "I’m not sure what you mean. You can ask me about tickets, tasks, approvals, vendors, inventory, expenses, travel, or reports.",
                source="Conci AI",
            )

        refined_response = chatbot_openai_refine(message, response)
        if refined_response and response.get("table"):
            refined_response["table"] = response["table"]
        return refined_response or response

    def inventory_item_for_identifier(identifier: int | str) -> dict:
        identifier_text = str(identifier).strip()
        if identifier_text.isdigit():
            item = repository.get_inventory_item(int(identifier_text))
            if item:
                return item
        return repository.get_inventory_item_by_item_id(identifier_text)

    def inventory_import_for_identifier(identifier: int | str) -> dict:
        identifier_text = str(identifier).strip()
        if not identifier_text.isdigit():
            return {}
        return repository.get_inventory_import_batch(int(identifier_text))

    def can_view_report(user: dict, report: dict) -> bool:
        if can_view_all(user):
            return True
        department = str(report.get("department", "")).strip().lower()
        report_type = str(report.get("report_type", "")).strip().lower()
        if can_manage_it(user):
            return department == "it" or report_type in {"it", "inventory", "security"}
        if can_manage_finance(user):
            return department == "finance" or report_type in {"finance", "expense", "expenses", "payment", "invoice"}
        if can_view_own_only(user):
            return department in {"employee", "general"} or report.get("uploaded_by_user_id") == user["id"]
        return False

    def can_manage_report(user: dict, report: dict) -> bool:
        if can_view_all(user):
            return True
        if can_view_own_only(user):
            return False
        return can_view_report(user, report)

    def can_manage_report_department(user: dict, department: str, report_type: str = "") -> bool:
        if can_view_all(user):
            return True
        normalized_department = department.strip().lower()
        normalized_type = report_type.strip().lower()
        if can_manage_it(user):
            return normalized_department == "it" or normalized_type in {"it", "inventory", "security"}
        if can_manage_finance(user):
            return normalized_department == "finance" or normalized_type in {"finance", "expense", "expenses", "payment", "invoice"}
        return False

    def visible_reports_for(
        user: dict,
        *,
        search: str = "",
        department: str = "All",
        report_type: str = "All",
        file_type: str = "All",
        status: str = "All",
        uploaded_date: str = "",
    ) -> list[dict]:
        normalized_search = search.strip().lower()
        visible = [report for report in repository.list_reports() if can_view_report(user, report)]
        filtered = []
        for report in visible:
            haystack = " ".join(
                [
                    report.get("report_id", ""),
                    report.get("report_name", ""),
                    report.get("report_type", ""),
                    report.get("department", ""),
                    report.get("uploaded_by_name", ""),
                    report.get("uploaded_by_email", ""),
                    report.get("file_type", ""),
                    report.get("status", ""),
                ]
            ).lower()
            if normalized_search and normalized_search not in haystack:
                continue
            if department != "All" and report.get("department") != department:
                continue
            if report_type != "All" and report.get("report_type") != report_type:
                continue
            if file_type != "All" and report.get("file_type") != file_type:
                continue
            if status != "All" and report.get("status") != status:
                continue
            if uploaded_date and str(report.get("uploaded_at", "")).slice(0, 10) != uploaded_date:
                continue
            filtered.append(report)
        return filtered

    def report_csv(reports: list[dict]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "report_id",
            "report_name",
            "report_type",
            "department",
            "uploaded_by",
            "uploaded_date",
            "file_type",
            "status",
            "notes",
        ])
        for report in reports:
            writer.writerow([
                report["report_id"],
                report["report_name"],
                report["report_type"],
                report["department"],
                report["uploaded_by_name"],
                report["uploaded_at"],
                report["file_type"],
                report["status"],
                report["notes"],
            ])
        return output.getvalue()

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "ai_mode": ai.mode, "agent_planner_mode": planner.mode}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest) -> dict:
        try:
            return auth.login(email=payload.email, password=payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.post("/api/auth/logout")
    def logout(
        token: str = Depends(current_token),
        user: dict = Depends(current_user),
    ) -> dict:
        auth.logout(token=token, user=user)
        return {"status": "logged_out"}

    @app.get("/api/auth/me")
    def me(user: dict = Depends(current_user)) -> dict:
        return {"user": public_user(user)}

    @app.get("/api/users")
    def users(_: dict = Depends(admin_user)) -> dict:
        return {"users": auth.list_users()}

    @app.get("/api/users/assignable")
    def assignable_users(user: dict = Depends(current_user)) -> dict:
        return {"users": assignable_users_for(user)}

    @app.post("/api/users")
    def create_user(payload: UserCreateRequest, actor: dict = Depends(admin_user)) -> dict:
        try:
            user = auth.create_user(actor=actor, payload=payload.model_dump())
            return {"user": user}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.patch("/api/users/{user_id}")
    def update_user(
        user_id: int,
        payload: UserUpdateRequest,
        actor: dict = Depends(admin_user),
    ) -> dict:
        try:
            user = auth.update_user(
                actor=actor,
                user_id=user_id,
                payload=payload.model_dump(exclude_unset=True),
            )
            return {"user": user}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/api/users/{user_id}/reset-password")
    def reset_password(
        user_id: int,
        payload: PasswordResetRequest,
        actor: dict = Depends(admin_user),
    ) -> dict:
        try:
            user = auth.reset_password(actor=actor, user_id=user_id, password=payload.password)
            return {"user": user}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.delete("/api/users/{user_id}")
    def delete_user(user_id: int, actor: dict = Depends(admin_user)) -> dict:
        try:
            user = auth.delete_user(actor=actor, user_id=user_id)
            return {"user": user}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/mock-data")
    def mock_data(_: dict = Depends(current_user)) -> dict:
        return get_mock_context()

    @app.post("/api/agent/plan")
    def plan_command(payload: CommandRequest, _: dict = Depends(current_user)) -> dict:
        try:
            plan = planner.create_plan(payload.message)
            return {
                "agent_plan": plan,
                "planner_mode": getattr(planner, "last_mode", planner.mode),
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/requests/route")
    def route_request(payload: RouteRequest, user: dict = Depends(current_user)) -> dict:
        route = rules.route_request(
            message=payload.message,
            requester_user_id=user["id"],
            task_type=payload.task_type,
            approval_type=payload.approval_type,
            metadata=payload.metadata,
        )
        request_record = repository.add_routed_request(message=payload.message, route=route)
        audit.record(
            "request.routed",
            route["status"],
            actor=user["email"],
            approval_required=route["approval_required"],
            approval_reason=route["approval_reason"] or None,
            details={
                "routed_request_id": request_record["id"],
                "task_type": route["task_type"],
                "assigned_role": route["assigned_role"],
                "required_approval_roles": route["required_approval_roles"],
                "requester_user_id": user["id"],
                "requester_role": user["role"],
            },
        )
        if route["approval_required"]:
            audit.record(
                "approval.rule.applied",
                "pending_approval",
                actor=user["email"],
                approval_required=True,
                approval_reason=route["approval_reason"],
                details={
                    "routed_request_id": request_record["id"],
                    "approval_type": route["approval_type"],
                    "required_approval_roles": route["required_approval_roles"],
                    "assigned_role": route["assigned_role"],
                },
            )
        return {"route": route, "request": request_record}

    @app.post("/api/chat/command")
    def run_command(payload: CommandRequest, user: dict = Depends(current_user)) -> dict:
        try:
            return workflow.run(payload.message, actor_user=user)
        except Exception as exc:
            audit.record(
                "workflow.failed",
                "failed",
                actor=user["email"],
                details={
                    "error": str(exc),
                    "command": payload.message,
                    "actor_user_id": user["id"],
                    "actor_role": user["role"],
                },
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/dashboard")
    def dashboard(user: dict = Depends(current_user)) -> dict:
        return dashboard_payload_for(user)

    @app.post("/api/chatbot/ask")
    def ask_chatbot(payload: ChatbotRequest, user: dict = Depends(current_user)) -> dict:
        response = chatbot_answer_for(user, payload.message)
        return {
            "answer": response["answer"],
            "bullets": response["bullets"],
            "source": response["source"],
            "response": response,
            "role": user["role"],
        }

    @app.post("/api/chat/assistant")
    async def chat_assistant(request: Request, user: dict = Depends(current_user)) -> dict:
        content_type = request.headers.get("content-type", "")
        if content_type.lower().startswith("multipart/form-data"):
            fields, files = parse_simple_multipart(content_type, await request.body())
            message = fields.get("message", "")
            uploaded_file = files.get("file")
            response = (
                chatbot_answer_for_file(
                    user,
                    message,
                    uploaded_file.get("filename", "attached-file"),
                    uploaded_file.get("content", b""),
                    uploaded_file.get("content_type", ""),
                )
                if uploaded_file
                else chatbot_answer_for(user, message)
            )
        else:
            payload_data = await request.json()
            payload = ChatbotRequest.model_validate(payload_data)
            response = chatbot_answer_for(user, payload.message)
        return {
            "answer": response["answer"],
            "bullets": response["bullets"],
            "source": response["source"],
            "response": response,
            "role": user["role"],
        }

    @app.get("/api/connectors")
    def list_connectors(user: dict = Depends(current_user)) -> dict:
        return {
            "connectors": repository.list_connectors(user["id"]),
            "message_templates": repository.list_message_templates(),
        }

    @app.post("/api/connectors/email/configure")
    def configure_email_connector(payload: EmailConnectorConfigRequest, user: dict = Depends(current_user)) -> dict:
        provider = payload.provider
        status = email_connector_status(provider)
        config = {
            "from_name": payload.from_name,
            "from_email": payload.from_email,
            "smtp_host": payload.smtp_host,
            "smtp_port": payload.smtp_port,
            "smtp_username": payload.smtp_username,
            "has_smtp_password": bool(payload.smtp_password),
            "has_sendgrid_api_key": bool(payload.sendgrid_api_key),
            "reply_to_email": payload.reply_to_email,
            "secrets_source": ".env only",
        }
        connector = repository.upsert_connector(user["id"], "email", provider, status, "Email", config)
        audit.record(
            "connector.email.configured",
            status,
            actor=user["email"],
            details={"provider": provider, "actor_user_id": user["id"], "actor_role": user["role"]},
        )
        return {"connector": connector}

    @app.post("/api/connectors/whatsapp/configure")
    def configure_whatsapp_connector(payload: WhatsAppConnectorConfigRequest, user: dict = Depends(current_user)) -> dict:
        provider = payload.provider
        status = whatsapp_connector_status(provider)
        config = {
            "business_phone_number": payload.business_phone_number,
            "has_twilio_account_sid": bool(payload.twilio_account_sid),
            "has_twilio_auth_token": bool(payload.twilio_auth_token),
            "twilio_whatsapp_sender_number": payload.twilio_whatsapp_sender_number,
            "has_whatsapp_cloud_api_access_token": bool(payload.whatsapp_cloud_api_access_token),
            "whatsapp_phone_number_id": payload.whatsapp_phone_number_id,
            "whatsapp_business_account_id": payload.whatsapp_business_account_id,
            "secrets_source": ".env only",
        }
        connector = repository.upsert_connector(user["id"], "whatsapp", provider, status, "WhatsApp", config)
        audit.record(
            "connector.whatsapp.configured",
            status,
            actor=user["email"],
            details={"provider": provider, "actor_user_id": user["id"], "actor_role": user["role"]},
        )
        return {"connector": connector}

    @app.post("/api/connectors/email/test")
    def test_email_connector(user: dict = Depends(current_user)) -> dict:
        connector = repository.get_connector("email", user["id"])
        payload = {
            "recipient_name": user["name"],
            "recipient_email": user["email"],
            "recipient_phone": "",
            "subject": "Agent Concierge email connector test",
            "message_body": "This is a test message from Agent Concierge.",
            "related_module": "settings",
            "related_record_id": "email-connector-test",
            "attachments": [],
        }
        logs = communications.send(user, payload, ["email"])
        connector = repository.upsert_connector(user["id"], "email", connector["provider"], connector["status"], "Email", connector.get("config", {}), datetime.now(timezone.utc).isoformat())
        return {"connector": connector, "logs": logs, "message": "Email connector test completed"}

    @app.post("/api/connectors/whatsapp/test")
    def test_whatsapp_connector(user: dict = Depends(current_user)) -> dict:
        connector = repository.get_connector("whatsapp", user["id"])
        business_phone = connector.get("config", {}).get("business_phone_number", "")
        payload = {
            "recipient_name": user["name"],
            "recipient_email": user["email"],
            "recipient_phone": business_phone,
            "subject": "Agent Concierge WhatsApp connector test",
            "message_body": "This is a test WhatsApp message from Agent Concierge.",
            "related_module": "settings",
            "related_record_id": "whatsapp-connector-test",
            "attachments": [],
        }
        logs = communications.send(user, payload, ["whatsapp"])
        connector = repository.upsert_connector(user["id"], "whatsapp", connector["provider"], connector["status"], "WhatsApp", connector.get("config", {}), datetime.now(timezone.utc).isoformat())
        return {"connector": connector, "logs": logs, "message": "WhatsApp connector test completed"}

    @app.post("/api/connectors/disconnect")
    def disconnect_connector(payload: ConnectorDisconnectRequest, user: dict = Depends(current_user)) -> dict:
        connector = repository.disconnect_connector(user["id"], payload.connector_type)
        audit.record(
            f"connector.{payload.connector_type}.disconnected",
            "not_connected",
            actor=user["email"],
            details={"actor_user_id": user["id"], "actor_role": user["role"]},
        )
        return {"connector": connector}

    @app.get("/api/communications/logs")
    def communication_logs(user: dict = Depends(current_user)) -> dict:
        logs = repository.list_communication_logs()
        if not can_view_all(user):
            logs = [log for log in logs if log.get("sent_by_user_id") == user["id"]]
        return {"logs": logs}

    def send_communication(payload: CommunicationSendRequest, channel: str, user: dict) -> dict:
        payload_data = payload.model_dump()
        payload_data["channel"] = channel
        if not can_send_communication(user, payload_data.get("related_module", "general")):
            raise HTTPException(status_code=403, detail="You do not have permission to send this message")
        channels = ["email", "whatsapp"] if channel == "both" else [channel]
        if "email" in channels and not payload_data.get("recipient_email"):
            raise HTTPException(status_code=400, detail="Recipient email is required for email messages")
        if "whatsapp" in channels and not payload_data.get("recipient_phone"):
            raise HTTPException(status_code=400, detail="Recipient phone is required for WhatsApp messages")
        logs = communications.send(user, payload_data, channels)
        statuses = {log.get("status") for log in logs}
        if statuses == {"mock_sent"}:
            message = "Mock message sent"
        elif "failed" in statuses:
            message = "Message send failed"
        else:
            message = "Message sent"
        return {"status": "ok", "message": message, "logs": logs}

    @app.post("/api/communications/send-email")
    def send_email(payload: CommunicationSendRequest, user: dict = Depends(current_user)) -> dict:
        return send_communication(payload, "email", user)

    @app.post("/api/communications/send-whatsapp")
    def send_whatsapp(payload: CommunicationSendRequest, user: dict = Depends(current_user)) -> dict:
        return send_communication(payload, "whatsapp", user)

    @app.post("/api/communications/send-both")
    def send_both(payload: CommunicationSendRequest, user: dict = Depends(current_user)) -> dict:
        return send_communication(payload, "both", user)

    @app.get("/api/approvals")
    def list_approvals(user: dict = Depends(current_user)) -> dict:
        return {"approvals": visible_approvals_for(user)}

    @app.get("/api/tasks")
    def list_tasks(user: dict = Depends(current_user)) -> dict:
        return {"tasks": visible_tasks_for(user)}

    @app.post("/api/tasks")
    def create_task(payload: TaskRequest, user: dict = Depends(current_user)) -> dict:
        task = repository.add_task(resolved_task_payload_for_user(payload, user))
        create_task_assignment_notification(task, user)
        audit.record(
            "task.created",
            "completed",
            actor=user["email"],
            details={
                "task_id": task["task_id"],
                "category": task["category"],
                "department": task["department"],
                "assigned_user_id": task.get("assigned_user_id"),
                "assigned_role": task["assigned_role"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"task": task}

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: int, user: dict = Depends(current_user)) -> dict:
        task = repository.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_view_task(user, task):
            raise HTTPException(status_code=403, detail="Task access not permitted")
        return {"task": task}

    @app.put("/api/tasks/{task_id}")
    def update_task(
        task_id: int,
        payload: TaskRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_manage_task(user, existing):
            raise HTTPException(status_code=403, detail="Task management not permitted")
        task = repository.update_task(task_id, **resolved_task_payload_for_user(payload, user))
        audit.record(
            "task.updated",
            "completed",
            actor=user["email"],
            details={
                "task_id": task["task_id"],
                "category": task["category"],
                "department": task["department"],
                "assigned_user_id": task.get("assigned_user_id"),
                "assigned_role": task["assigned_role"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"task": task}

    @app.patch("/api/tasks/{task_id}/status")
    def update_task_status(
        task_id: int,
        payload: TaskStatusUpdateRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_manage_task(user, existing):
            raise HTTPException(status_code=403, detail="Task management not permitted")
        task = repository.update_task_status(task_id, payload.status)
        audit.record(
            "task.status_changed",
            "completed",
            actor=user["email"],
            details={
                "task_id": task["task_id"],
                "previous_status": existing["status"],
                "status": task["status"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"task": task}

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: int, user: dict = Depends(current_user)) -> dict:
        existing = repository.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_manage_task(user, existing):
            raise HTTPException(status_code=403, detail="Task management not permitted")
        deleted = repository.delete_task(task_id)
        audit.record(
            "task.deleted",
            "completed",
            actor=user["email"],
            details={
                "task_id": deleted["task_id"],
                "category": deleted["category"],
                "department": deleted["department"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"task": deleted}

    @app.get("/api/tickets")
    def list_tickets(user: dict = Depends(current_user)) -> dict:
        return {"tickets": visible_tickets_for(user)}

    @app.get("/api/notifications")
    def list_notifications(user: dict = Depends(current_user)) -> dict:
        notifications = visible_notifications_for(user)
        return {
            "notifications": notifications,
            "unread_count": len([notification for notification in notifications if notification["unread"]]),
        }

    @app.patch("/api/notifications/{notification_id}/read")
    def mark_notification_read(notification_id: int, user: dict = Depends(current_user)) -> dict:
        notification = repository.get_notification(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        if not can_view_notification(user, notification):
            raise HTTPException(status_code=403, detail="Notification access not permitted")
        updated = repository.mark_notification_read(notification_id, user["id"])
        visible = serialize_notification(user, updated)
        return {"notification": visible}

    @app.patch("/api/notifications/read-all")
    def mark_all_notifications_read(user: dict = Depends(current_user)) -> dict:
        notifications = [
            notification
            for notification in repository.list_notifications(limit=100)
            if can_view_notification(user, notification)
        ]
        for notification in notifications:
            repository.mark_notification_read(notification["id"], user["id"])
        return {"notifications": visible_notifications_for(user), "unread_count": 0}

    @app.post("/api/tickets")
    def create_ticket(payload: TicketCreateRequest, user: dict = Depends(current_user)) -> dict:
        assignment = ticket_assignment(payload.ticket_type, payload.category)
        ticket_payload = payload.model_dump()
        ticket_payload["status"] = "Open"
        ticket = repository.add_ticket(
            {
                **ticket_payload,
                **assignment,
                "requester_user_id": user["id"],
                "requester_name": user["name"],
                "requester_email": user["email"],
                "requester_role": user["role"],
            }
        )
        audit.record(
            "ticket.created",
            "completed",
            actor=user["email"],
            approval_required=ticket["approval_required"],
            details={
                "ticket_id": ticket["ticket_id"],
                "ticket_type": ticket["ticket_type"],
                "category": ticket["category"],
                "assigned_role": ticket["assigned_role"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        create_ticket_notification(
            ticket,
            "ticket.created",
            "New ticket created",
            f"New ticket created: {ticket['title']}",
        )
        return {"ticket": ticket}

    @app.put("/api/tickets/{ticket_id}")
    def update_ticket(
        ticket_id: int,
        payload: TicketUpdateRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_ticket(ticket_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not can_manage_ticket(user, existing):
            raise HTTPException(status_code=403, detail="Ticket management not permitted")
        previous_status = existing["status"]
        assignment = ticket_assignment(payload.ticket_type, payload.category)
        ticket = repository.update_ticket(
            ticket_id,
            **payload.model_dump(),
            **assignment,
        )
        audit.record(
            "ticket.updated",
            "completed",
            actor=user["email"],
            approval_required=ticket["approval_required"],
            details={
                "ticket_id": ticket["ticket_id"],
                "ticket_type": ticket["ticket_type"],
                "category": ticket["category"],
                "assigned_role": ticket["assigned_role"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        if ticket["status"] != previous_status:
            create_ticket_status_notification(ticket)
        return {"ticket": ticket}

    @app.patch("/api/tickets/{ticket_id}/status")
    def update_ticket_status(
        ticket_id: int,
        payload: TicketStatusUpdateRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_ticket(ticket_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not can_manage_ticket(user, existing):
            raise HTTPException(status_code=403, detail="Ticket management not permitted")
        ticket = repository.update_ticket_status(ticket_id, payload.status)
        audit.record(
            "ticket.status_changed",
            "completed",
            actor=user["email"],
            approval_required=ticket["approval_required"],
            details={
                "ticket_id": ticket["ticket_id"],
                "ticket_type": ticket["ticket_type"],
                "status": ticket["status"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        if ticket["status"] != existing["status"]:
            create_ticket_status_notification(ticket)
        return {"ticket": ticket}

    @app.get("/api/expenses")
    def list_expenses(user: dict = Depends(current_user)) -> dict:
        return {"expenses": visible_expenses_for(user)}

    @app.post("/api/expenses")
    def create_expense(payload: ExpenseCreateRequest, user: dict = Depends(current_user)) -> dict:
        expense_payload = expense_payload_for_user(payload, user)
        try:
            expense = repository.add_expense(expense_payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "expense.created",
            "completed",
            actor=user["email"],
            approval_required=expense["approval_required"],
            approval_reason="Finance approval required" if expense["approval_required"] else None,
            details={
                "expense_id": expense["expense_id"],
                "category": expense["category"],
                "amount": expense["amount"],
                "currency": expense["currency"],
                "status": expense["status"],
                "policy_exceptions": expense["policy_exceptions"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"expense": expense}

    @app.post("/api/expenses/import/preview")
    def preview_expense_import(
        payload: ExpenseImportPreviewRequest,
        _: dict = Depends(expense_import_user),
    ) -> dict:
        try:
            return preview_expense_file(payload.filename, payload.content_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/expenses/import/confirm")
    def confirm_expense_import(
        payload: ExpenseImportConfirmRequest,
        user: dict = Depends(expense_import_user),
    ) -> dict:
        duplicate_ids: list[str] = []
        seen_ids: set[str] = set()
        for item in payload.items:
            expense_id = item.expense_id.strip()
            if expense_id in seen_ids or repository.get_expense_by_expense_id(expense_id):
                duplicate_ids.append(expense_id)
            seen_ids.add(expense_id)
        if duplicate_ids:
            raise HTTPException(status_code=400, detail=f"Expense ID already exists: {', '.join(duplicate_ids)}")

        imported_expenses = []
        for item in payload.items:
            expense_payload = expense_payload_for_user(item, user)
            try:
                imported_expenses.append(repository.add_expense(expense_payload))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "expense.imported",
            "completed",
            actor=user["email"],
            details={
                "file_name": payload.filename,
                "imported_count": len(imported_expenses),
                "expense_ids": [expense["expense_id"] for expense in imported_expenses],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {
            "expenses": imported_expenses,
            "import": {
                "file_name": payload.filename,
                "successful_rows": len(imported_expenses),
                "failed_rows": 0,
                "status": "Completed",
            },
        }

    @app.put("/api/expenses/{expense_id}")
    def update_expense(
        expense_id: int,
        payload: ExpenseUpdateRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_expense(expense_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Expense not found")
        if not can_manage_expense(user, existing):
            raise HTTPException(status_code=403, detail="Expense management not permitted")
        expense_payload = expense_payload_for_user(payload, user, existing)
        if existing.get("approved_by") and "approved_by" not in expense_payload:
            expense_payload["approved_by"] = existing["approved_by"]
        expense = repository.update_expense(expense_id, **expense_payload)
        audit.record(
            "expense.updated",
            "completed",
            actor=user["email"],
            approval_required=expense["approval_required"],
            approval_reason="Finance approval required" if expense["approval_required"] else None,
            details={
                "expense_id": expense["expense_id"],
                "category": expense["category"],
                "amount": expense["amount"],
                "status": expense["status"],
                "policy_exceptions": expense["policy_exceptions"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"expense": expense}

    @app.patch("/api/expenses/{expense_id}/status")
    def update_expense_status(
        expense_id: int,
        payload: ExpenseStatusUpdateRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        existing = repository.get_expense(expense_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Expense not found")
        if payload.status in {"Approved", "Rejected", "Paid", "Reimbursed"}:
            if not (can_view_all(user) or can_manage_finance(user)):
                raise HTTPException(status_code=403, detail="Finance approval required")
        elif not can_manage_expense(user, existing):
            raise HTTPException(status_code=403, detail="Expense management not permitted")
        approved_by = user["name"] if payload.status in {"Approved", "Paid", "Reimbursed"} else existing.get("approved_by", "")
        expense = repository.update_expense_status(expense_id, payload.status, approved_by=approved_by)
        audit.record(
            "expense.status_changed",
            "completed",
            actor=user["email"],
            approval_required=expense["approval_required"],
            approval_reason="Finance approval required" if expense["approval_required"] else None,
            details={
                "expense_id": expense["expense_id"],
                "status": expense["status"],
                "approved_by": expense["approved_by"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"expense": expense}

    @app.get("/api/travel")
    def list_travel_records(_: dict = Depends(travel_user)) -> dict:
        return {"travel_records": repository.list_travel_records()}

    @app.get("/api/travel/summary")
    def travel_summary(_: dict = Depends(travel_user)) -> dict:
        return repository.travel_summary()

    @app.post("/api/travel")
    def create_travel_record(
        payload: TravelRecordRequest,
        user: dict = Depends(travel_user),
    ) -> dict:
        try:
            record = repository.add_travel_record(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "travel.created",
            "completed",
            actor=user["email"],
            approval_required=record["approval_status"] in {"Submitted", "Pending Approval", "Needs Info"},
            approval_reason="Travel approval required" if record["approval_status"] in {"Submitted", "Pending Approval", "Needs Info"} else None,
            details={
                "travel_id": record["travel_id"],
                "employee_email": record["employee_email"],
                "department": record["department"],
                "destination_to": record["destination_to"],
                "actual_spend": record["actual_spend"],
                "policy_status": record["policy_status"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"travel_record": record}

    @app.put("/api/travel/{travel_row_id}")
    def update_travel_record(
        travel_row_id: int,
        payload: TravelRecordRequest,
        user: dict = Depends(travel_user),
    ) -> dict:
        if not repository.get_travel_record(travel_row_id):
            raise HTTPException(status_code=404, detail="Travel record not found")
        try:
            record = repository.update_travel_record(travel_row_id, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "travel.updated",
            "completed",
            actor=user["email"],
            approval_required=record["approval_status"] in {"Submitted", "Pending Approval", "Needs Info"},
            approval_reason="Travel approval required" if record["approval_status"] in {"Submitted", "Pending Approval", "Needs Info"} else None,
            details={
                "travel_id": record["travel_id"],
                "employee_email": record["employee_email"],
                "department": record["department"],
                "destination_to": record["destination_to"],
                "actual_spend": record["actual_spend"],
                "policy_status": record["policy_status"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"travel_record": record}

    @app.get("/api/calendar-events")
    def list_calendar_events(_: dict = Depends(travel_user)) -> dict:
        return {"calendar_events": repository.list_calendar_events()}

    @app.post("/api/calendar-events")
    def create_calendar_event(
        payload: CalendarEventRequest,
        user: dict = Depends(travel_user),
    ) -> dict:
        try:
            event = repository.add_calendar_event(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "calendar_event.created",
            "completed",
            actor=user["email"],
            details={
                "event_id": event["event_id"],
                "title": event["title"],
                "event_type": event["event_type"],
                "related_travel_id": event["related_travel_id"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"calendar_event": event}

    @app.put("/api/calendar-events/{event_row_id}")
    def update_calendar_event(
        event_row_id: int,
        payload: CalendarEventRequest,
        user: dict = Depends(travel_user),
    ) -> dict:
        if not repository.get_calendar_event(event_row_id):
            raise HTTPException(status_code=404, detail="Calendar event not found")
        try:
            event = repository.update_calendar_event(event_row_id, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "calendar_event.updated",
            "completed",
            actor=user["email"],
            details={
                "event_id": event["event_id"],
                "title": event["title"],
                "event_type": event["event_type"],
                "related_travel_id": event["related_travel_id"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"calendar_event": event}

    @app.get("/api/reports")
    def list_reports(user: dict = Depends(current_user)) -> dict:
        return {"reports": visible_reports_for(user)}

    @app.post("/api/reports/import")
    def import_report(payload: ReportImportRequest, user: dict = Depends(current_user)) -> dict:
        if not can_manage_report_department(user, payload.department, payload.report_type):
            raise HTTPException(status_code=403, detail="Report import not permitted for this department")
        try:
            file_content = base64.b64decode(payload.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid report file content") from exc
        try:
            report = repository.add_report(
                {
                    **payload.model_dump(exclude={"content_base64"}),
                    "uploaded_by_user_id": user["id"],
                    "uploaded_by_name": user["name"],
                    "uploaded_by_email": user["email"],
                    "uploaded_by_role": user["role"],
                    "status": "Ready",
                },
                file_content,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "report.imported",
            "completed",
            actor=user["email"],
            details={
                "report_id": report["report_id"],
                "report_name": report["report_name"],
                "report_type": report["report_type"],
                "department": report["department"],
                "file_type": report["file_type"],
                "file_size": report["file_size"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"report": report}

    @app.get("/api/reports/export")
    def export_reports(
        search: str = Query(default=""),
        department: str = Query(default="All"),
        report_type: str = Query(default="All"),
        file_type: str = Query(default="All"),
        status: str = Query(default="All"),
        uploaded_date: str = Query(default=""),
        user: dict = Depends(current_user),
    ) -> Response:
        if can_view_own_only(user):
            raise HTTPException(status_code=403, detail="Report export not permitted")
        reports = visible_reports_for(
            user,
            search=search,
            department=department,
            report_type=report_type,
            file_type=file_type,
            status=status,
            uploaded_date=uploaded_date,
        )
        audit.record(
            "report.exported",
            "completed",
            actor=user["email"],
            details={
                "exported_count": len(reports),
                "search": search,
                "department": department,
                "report_type": report_type,
                "file_type": file_type,
                "status": status,
                "uploaded_date": uploaded_date,
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return Response(
            report_csv(reports),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="reports_export.csv"'},
        )

    @app.get("/api/reports/{report_id}/download")
    def download_report(report_id: int, user: dict = Depends(current_user)) -> FileResponse:
        report = repository.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not can_view_report(user, report) or can_view_own_only(user):
            raise HTTPException(status_code=403, detail="Report download not permitted")
        file_path = Path(report["stored_file_path"])
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Report file not found")
        audit.record(
            "report.exported",
            "completed",
            actor=user["email"],
            details={
                "report_id": report["report_id"],
                "downloaded_file": report["file_name"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        media_type = {
            "CSV": "text/csv",
            "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "PDF": "application/pdf",
        }.get(report["file_type"], "application/octet-stream")
        return FileResponse(file_path, media_type=media_type, filename=report["file_name"])

    @app.delete("/api/reports/{report_id}")
    def delete_report(report_id: int, user: dict = Depends(current_user)) -> dict:
        report = repository.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not can_manage_report(user, report):
            raise HTTPException(status_code=403, detail="Report delete not permitted")
        deleted = repository.delete_report(report_id)
        audit.record(
            "report.deleted",
            "completed",
            actor=user["email"],
            details={
                "report_id": deleted["report_id"],
                "report_name": deleted["report_name"],
                "department": deleted["department"],
                "file_type": deleted["file_type"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"report": deleted}

    @app.get("/api/vendors")
    def list_vendors(_: dict = Depends(vendor_viewer_user)) -> dict:
        return {"vendors": repository.list_vendors()}

    @app.get("/api/inventory")
    def list_inventory(_: dict = Depends(inventory_viewer_user)) -> dict:
        return {"inventory_items": repository.list_inventory_items()}

    @app.post("/api/inventory")
    def create_inventory_item(
        payload: InventoryItemRequest,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        try:
            item = repository.add_inventory_item(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "inventory.created",
            "completed",
            actor=user["email"],
            details={
                "inventory_id": item["id"],
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "category": item["category"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"inventory_item": item}

    @app.post("/api/inventory/import/preview")
    def preview_inventory_import(
        payload: InventoryImportPreviewRequest,
        _: dict = Depends(inventory_manager_user),
    ) -> dict:
        try:
            return preview_inventory_file(payload.filename, payload.content_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/inventory/imports")
    def list_inventory_imports(_: dict = Depends(inventory_viewer_user)) -> dict:
        return {"imports": repository.list_inventory_import_batches()}

    @app.post("/api/inventory/imports")
    def create_inventory_import(
        payload: InventoryImportCreateRequest,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        batch = repository.add_inventory_import_batch(
            {
                "file_name": payload.filename,
                "imported_by_user_id": user["id"],
                "imported_by_name": user["name"],
                "imported_by_email": user["email"],
                "total_rows": len(payload.items),
                "successful_rows": 0,
                "failed_rows": 0,
                "status": "Failed",
                "notes": "",
            }
        )
        imported_items = []
        failures = []
        for index, item_payload in enumerate(payload.items, start=1):
            try:
                imported_items.append(
                    repository.add_inventory_item(
                        {
                            **item_payload.model_dump(),
                            "import_batch_id": batch["id"],
                        }
                    )
                )
            except ValueError as exc:
                failures.append({"row": index, "item_id": item_payload.item_id, "error": str(exc)})
        successful_rows = len(imported_items)
        failed_rows = len(failures)
        if successful_rows and failed_rows:
            status = "Partially Imported"
        elif successful_rows:
            status = "Completed"
        else:
            status = "Failed"
        batch = repository.update_inventory_import_batch(
            batch["id"],
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            status=status,
            notes="; ".join([f"Row {failure['row']} {failure['item_id']}: {failure['error']}" for failure in failures]),
        )
        audit.record(
            "inventory.import.created",
            "completed" if successful_rows else "failed",
            actor=user["email"],
            details={
                "import_id": batch["id"],
                "file_name": batch["file_name"],
                "total_rows": batch["total_rows"],
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "status": status,
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"import": batch, "inventory_items": imported_items, "failures": failures}

    @app.get("/api/inventory/imports/{import_id}/items")
    def inventory_import_items(import_id: str, _: dict = Depends(inventory_viewer_user)) -> dict:
        if import_id == "legacy-unbatched":
            return {
                "import": next(
                    (batch for batch in repository.list_inventory_import_batches() if batch["id"] == "legacy-unbatched"),
                    {},
                ),
                "inventory_items": repository.list_unbatched_inventory_items(),
            }
        batch = inventory_import_for_identifier(import_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Inventory import not found")
        return {"import": batch, "inventory_items": repository.list_inventory_items_for_import(batch["id"])}

    @app.put("/api/inventory/{inventory_id}")
    def update_inventory_item(
        inventory_id: int,
        payload: InventoryItemRequest,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        if not repository.get_inventory_item(inventory_id):
            raise HTTPException(status_code=404, detail="Inventory item not found")
        try:
            item = repository.update_inventory_item(inventory_id, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record(
            "inventory.updated",
            "completed",
            actor=user["email"],
            details={
                "inventory_id": item["id"],
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "category": item["category"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"inventory_item": item}

    @app.patch("/api/inventory/{item_id}/status")
    def update_inventory_status(
        item_id: str,
        payload: InventoryStatusUpdateRequest,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        existing = inventory_item_for_identifier(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        item = repository.update_inventory_item(existing["id"], {**existing, "status": payload.status})
        audit.record(
            "inventory.status_updated",
            "completed",
            actor=user["email"],
            details={
                "inventory_id": item["id"],
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "status": item["status"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"inventory_item": item}

    @app.delete("/api/inventory/{item_id}")
    def delete_inventory_item(
        item_id: str,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        existing = inventory_item_for_identifier(item_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        item = repository.delete_inventory_item(existing["id"])
        audit.record(
            "inventory.item.deleted",
            "completed",
            actor=user["email"],
            details={
                "inventory_id": item["id"],
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "category": item["category"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"inventory_item": item}

    @app.post("/api/inventory/bulk-delete")
    def bulk_delete_inventory_items(
        payload: InventoryBulkDeleteRequest,
        user: dict = Depends(inventory_manager_user),
    ) -> dict:
        items = []
        missing = []
        seen_ids = set()
        for identifier in payload.item_ids:
            item = inventory_item_for_identifier(identifier)
            if not item:
                missing.append(str(identifier))
                continue
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            items.append(item)
        if missing:
            raise HTTPException(status_code=404, detail=f"Inventory item not found: {', '.join(missing)}")
        deleted_items = repository.delete_inventory_items([item["id"] for item in items])
        audit.record(
            "inventory.items.bulk_deleted",
            "completed",
            actor=user["email"],
            details={
                "inventory_ids": [item["id"] for item in deleted_items],
                "item_ids": [item["item_id"] for item in deleted_items],
                "deleted_count": len(deleted_items),
                "selection_mode": payload.selection_mode or "selected_rows",
                "search": payload.search or "",
                "filters": payload.filters,
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"deleted_items": deleted_items, "deleted_count": len(deleted_items)}

    @app.delete("/api/inventory/imports/{import_id}")
    def delete_inventory_import(import_id: str, user: dict = Depends(inventory_manager_user)) -> dict:
        if import_id == "legacy-unbatched":
            if not can_view_all(user):
                raise HTTPException(status_code=403, detail="Admin role required for legacy unbatched cleanup")
            deleted_items = repository.delete_unbatched_inventory_items()
            audit.record(
                "inventory.import.deleted",
                "completed",
                actor=user["email"],
                details={
                    "import_id": import_id,
                    "file_name": "Legacy unbatched inventory",
                    "deleted_count": len(deleted_items),
                    "item_ids": [item["item_id"] for item in deleted_items],
                    "actor_user_id": user["id"],
                    "actor_role": user["role"],
                },
            )
            return {
                "import": {
                    "id": import_id,
                    "file_name": "Legacy unbatched inventory",
                    "status": "Deleted",
                    "deleted_count": len(deleted_items),
                    "is_legacy_unbatched": True,
                },
                "deleted_items": deleted_items,
                "deleted_count": len(deleted_items),
            }
        batch = inventory_import_for_identifier(import_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Inventory import not found")
        deleted_items = repository.delete_inventory_import_batch_items(batch["id"])
        updated_batch = repository.get_inventory_import_batch(batch["id"])
        audit.record(
            "inventory.import.deleted",
            "completed",
            actor=user["email"],
            details={
                "import_id": batch["id"],
                "file_name": batch["file_name"],
                "deleted_count": len(deleted_items),
                "item_ids": [item["item_id"] for item in deleted_items],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"import": updated_batch, "deleted_items": deleted_items, "deleted_count": len(deleted_items)}

    @app.post("/api/vendors")
    def create_vendor(payload: VendorCreateRequest, user: dict = Depends(vendor_manager_user)) -> dict:
        vendor = repository.add_vendor(
            {
                **payload.model_dump(),
                "status": "active",
                "created_by_user_id": user["id"],
            }
        )
        audit.record(
            "vendor.created",
            "completed",
            actor=user["email"],
            details={
                "vendor_id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"vendor": vendor}

    @app.put("/api/vendors/{vendor_id}")
    def update_vendor(
        vendor_id: int,
        payload: VendorUpdateRequest,
        user: dict = Depends(vendor_manager_user),
    ) -> dict:
        existing = repository.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")
        vendor = repository.update_vendor(
            vendor_id,
            {
                **payload.model_dump(),
                "status": existing.get("status", "active"),
            },
        )
        audit.record(
            "vendor.updated",
            "completed",
            actor=user["email"],
            details={
                "vendor_id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"vendor": vendor}

    @app.patch("/api/vendors/{vendor_id}/close")
    @app.post("/api/vendors/{vendor_id}/close")
    def close_vendor(vendor_id: int, user: dict = Depends(vendor_manager_user)) -> dict:
        existing = repository.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")
        end_date = existing.get("end_date") or datetime.now(timezone.utc).date().isoformat()
        vendor = repository.update_vendor(vendor_id, {"status": "closed", "end_date": end_date})
        audit.record(
            "vendor.closed",
            "completed",
            actor=user["email"],
            details={
                "vendor_id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "end_date": vendor["end_date"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"vendor": vendor}

    @app.patch("/api/vendors/{vendor_id}/reopen")
    @app.post("/api/vendors/{vendor_id}/reopen")
    def reopen_vendor(vendor_id: int, user: dict = Depends(vendor_manager_user)) -> dict:
        existing = repository.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")
        vendor = repository.update_vendor(vendor_id, {"status": "active"})
        audit.record(
            "vendor.reopened",
            "completed",
            actor=user["email"],
            details={
                "vendor_id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "end_date": vendor["end_date"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        return {"vendor": vendor}

    @app.post("/api/vendors/{vendor_id}/email")
    def send_vendor_email(
        vendor_id: int,
        payload: VendorEmailRequest,
        user: dict = Depends(vendor_manager_user),
    ) -> dict:
        vendor = repository.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        route = rules.apply_rule(
            task_type="vendor_management",
            approval_type="external_vendor_email",
            requester_user_id=user["id"],
        ).to_dict()
        audit.record(
            "vendor.email.drafted",
            "pending_approval",
            actor=user["email"],
            approval_required=True,
            approval_reason=route["approval_reason"],
            details={
                "vendor_id": vendor["id"],
                "vendor_name": vendor["vendor_name"],
                "recipient_email": vendor["email"],
                "subject": payload.subject,
                "assigned_role": route["assigned_role"],
                "required_approval_roles": route["required_approval_roles"],
                "actor_user_id": user["id"],
                "actor_role": user["role"],
            },
        )
        approval = approvals.queue_external_email(
            recipient_name=vendor["contact_person"],
            recipient_email=vendor["email"],
            subject=payload.subject,
            body=payload.body,
            related_meeting_id=None,
            requester_user_id=user["id"],
        )
        return {
            "status": "pending_approval",
            "message": "Vendor email sent to approval queue",
            "approval": approval,
            "route": route,
        }

    @app.patch("/api/approvals/{approval_id}")
    def decide_approval(
        approval_id: int,
        payload: ApprovalDecisionRequest,
        user: dict = Depends(current_user),
    ) -> dict:
        try:
            approval = approvals.decide(
                approval_id,
                action=payload.action,
                subject=payload.subject,
                body=payload.body,
                reason=payload.reason,
                actor_user=user,
            )
            return {"approval": approval, "dashboard": repository.dashboard()}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/audit-log")
    def audit_log(_: dict = Depends(current_user)) -> dict:
        return {"audit_logs": repository.list_audit_logs()}

    @app.post("/api/dev/reset")
    def reset_demo(user: dict = Depends(admin_user)) -> dict:
        repository.reset()
        repository.seed_demo_users()
        repository.seed_demo_tasks()
        repository.seed_demo_tickets()
        repository.seed_demo_expenses()
        repository.seed_demo_inventory()
        repository.seed_demo_travel()
        repository.seed_demo_reports()
        repository.seed_message_templates()
        audit.record(
            "demo.reset",
            "completed",
            actor=user["email"],
            details={"actor_user_id": user["id"], "actor_role": user["role"]},
        )
        return {"status": "reset", "dashboard": repository.dashboard()}

    return app


app = create_app()
