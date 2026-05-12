import base64
import io
import json
import os
import sqlite3
import sys
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.repositories.admin_repository import AdminRepository
from app.main import create_app
from app.core.config import deepinfra_api_key_from_env, openai_api_key_from_env, settings
from app.services.agent_planner import (
    MockAdminAgentPlanner,
    OpenAIResponsesAdminAgentPlanner,
    get_agent_planner,
)
from app.services.approval_rules import ApprovalRulesService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.deepinfra_service import DeepInfraChatClient, get_deepinfra_client, parse_json_object
from app.services.mock_ai import MockAdminAI
from app.services.policy import approval_reason, can_auto_execute, requires_approval
from app.services.workflow import VendorReviewWorkflow


class VendorWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.repo = AdminRepository(Path(self.tmp.name) / "test.db")
        self.repo.init_schema()
        self.audit = AuditService(self.repo)
        self.approvals = ApprovalService(self.repo, self.audit)
        self.workflow = VendorReviewWorkflow(
            repository=self.repo,
            audit=self.audit,
            approvals=self.approvals,
            ai=MockAdminAI(),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def api_client(self):
        from fastapi.testclient import TestClient

        app = create_app(database_path=Path(self.tmp.name) / "api.db")
        return TestClient(app), app

    def auth_headers(self, client, email="admin@company.com", password="admin123"):
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['token']}"}

    def add_mock_approval(self, app, approval_type: str) -> dict:
        return app.state.repository.add_approval(
            {
                "approval_type": approval_type,
                "status": "pending",
                "risk_reason": f"{approval_type} requires approval.",
                "recipient_name": "Internal Reviewer",
                "recipient_email": "review@example.com",
                "subject": f"{approval_type} request",
                "body": "Please review.",
                "original_body": "Please review.",
                "related_meeting_id": None,
            }
        )

    def ticket_payload(self, **overrides):
        payload = {
            "ticket_type": "IT",
            "title": "Need VPN access",
            "description": "Please enable VPN access for remote work.",
            "category": "Software Access",
            "priority": "Medium",
            "status": "Open",
            "due_date": "2026-05-15",
            "approval_required": True,
        }
        payload.update(overrides)
        return payload

    def task_payload(self, **overrides):
        payload = {
            "title": "Prepare asset handover",
            "description": "Prepare the laptop handover checklist and confirm accessories.",
            "category": "IT",
            "department": "IT",
            "assigned_to": "IT Manager",
            "assigned_role": "it_manager",
            "priority": "Medium",
            "status": "Open",
            "due_date": "2026-05-15",
            "notes": "Created by backend test.",
        }
        payload.update(overrides)
        return payload

    def inventory_payload(self, **overrides):
        payload = {
            "item_id": "INV-TEST-1001",
            "item_name": "Test Laptop",
            "category": "IT Equipment",
            "subcategory": "Laptop",
            "brand": "Lenovo",
            "model": "ThinkPad T14",
            "serial_number": "TP-T14-001",
            "quantity": 2,
            "unit": "pcs",
            "condition": "Good",
            "location": "IT Store",
            "assigned_to": "",
            "department": "IT",
            "purchase_date": "2026-04-01",
            "warranty_end_date": "2029-03-31",
            "vendor": "Tech Supplies",
            "minimum_stock_level": 1,
            "status": "Available",
            "notes": "Test inventory item.",
        }
        payload.update(overrides)
        return payload

    def expense_payload(self, **overrides):
        payload = {
            "employee_name": "Employee User",
            "employee_email": "employee@company.com",
            "department": "Operations",
            "category": "Travel",
            "vendor_merchant": "Indigo Airlines",
            "amount": 12500,
            "currency": "INR",
            "expense_date": "2026-05-08",
            "payment_mode": "Corporate Card",
            "receipt_status": "Attached",
            "receipt_attachment_name": "receipt.pdf",
            "notes": "Client visit travel.",
            "status": "Submitted",
            "approval_required": True,
        }
        payload.update(overrides)
        return payload

    def travel_payload(self, **overrides):
        payload = {
            "travel_id": "TRV-TEST-1001",
            "employee_name": "Admin User",
            "employee_email": "admin@company.com",
            "department": "Admin",
            "destination_from": "Pune",
            "destination_to": "Delhi",
            "travel_start_date": "2026-05-18",
            "travel_end_date": "2026-05-20",
            "purpose": "Vendor review visit",
            "travel_mode": "Flight",
            "estimated_budget": 32000,
            "actual_spend": 28500,
            "number_of_trips": 1,
            "approval_status": "Approved",
            "policy_status": "Within Policy",
            "booking_status": "Booked",
            "notes": "Test travel record.",
            "google_calendar_event_id": "",
            "google_sync_status": "Not Synced",
            "google_last_synced_at": None,
        }
        payload.update(overrides)
        return payload

    def calendar_event_payload(self, **overrides):
        payload = {
            "event_id": "CAL-TEST-1001",
            "title": "Vendor travel planning",
            "event_type": "Travel",
            "start_datetime": "2026-05-18T09:00:00",
            "end_datetime": "2026-05-18T10:00:00",
            "location": "Pune",
            "attendees": "Admin User",
            "related_travel_id": "TRV-TEST-1001",
            "reminder": "1 day before",
            "notes": "Test calendar event.",
            "status": "Scheduled",
            "google_calendar_event_id": "",
            "google_sync_status": "Not Synced",
            "google_last_synced_at": None,
        }
        payload.update(overrides)
        return payload

    def report_import_payload(self, **overrides):
        content = overrides.pop("content", b"column,value\nsample,1\n")
        payload = {
            "report_name": "Test Report",
            "report_type": "Operations",
            "department": "Admin",
            "notes": "Imported during backend test.",
            "filename": "test-report.csv",
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
        payload.update(overrides)
        return payload

    def inventory_import_payload(self, filename: str, content: bytes) -> dict:
        return {
            "filename": filename,
            "content_base64": base64.b64encode(content).decode("ascii"),
        }

    def make_xlsx(self, rows: list[list[str]]) -> bytes:
        shared_values = []
        shared_index = {}

        def shared_id(value: str) -> int:
            if value not in shared_index:
                shared_index[value] = len(shared_values)
                shared_values.append(value)
            return shared_index[value]

        def column_name(index: int) -> str:
            name = ""
            index += 1
            while index:
                index, remainder = divmod(index - 1, 26)
                name = chr(ord("A") + remainder) + name
            return name

        row_xml = []
        for row_number, row in enumerate(rows, start=1):
            cells = []
            for column_index, value in enumerate(row):
                cell_ref = f"{column_name(column_index)}{row_number}"
                cells.append(f'<c r="{cell_ref}" t="s"><v>{shared_id(value)}</v></c>')
            row_xml.append(f'<row r="{row_number}">{"".join(cells)}</row>')

        shared_xml = "".join(
            f"<si><t>{value}</t></si>" for value in shared_values
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as workbook:
            workbook.writestr(
                "xl/workbook.xml",
                """
                <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                  <sheets><sheet name="Inventory" sheetId="1" r:id="rId1"/></sheets>
                </workbook>
                """,
            )
            workbook.writestr(
                "xl/_rels/workbook.xml.rels",
                """
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
                </Relationships>
                """,
            )
            workbook.writestr(
                "xl/sharedStrings.xml",
                f"""
                <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_values)}" uniqueCount="{len(shared_values)}">
                  {shared_xml}
                </sst>
                """,
            )
            workbook.writestr(
                "xl/worksheets/sheet1.xml",
                f"""
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData>{"".join(row_xml)}</sheetData>
                </worksheet>
                """,
            )
        return buffer.getvalue()

    def find_ticket(self, tickets: list[dict], ticket_number: str) -> dict:
        return next(ticket for ticket in tickets if ticket["ticket_id"] == ticket_number)

    def test_vendor_review_workflow_creates_meeting_tasks_approval_and_audit(self):
        result = self.workflow.run(
            "Plan tomorrow's vendor review meeting, remind everyone, prepare files, "
            "take notes during the meeting, and follow up on action items."
        )

        self.assertEqual(result["agent_plan"]["task_type"], "vendor_management")
        self.assertEqual(result["agent_plan"]["automation_level"], "needs_human_approval")
        self.assertTrue(result["agent_plan"]["approval_required"])
        self.assertEqual(result["meeting"]["status"], "scheduled")
        self.assertEqual(len(result["meeting"]["files"]), 3)
        self.assertEqual(len(result["decisions"]), 3)
        self.assertEqual(len(result["action_items"]), 3)
        self.assertEqual(result["approval"]["status"], "pending")
        self.assertEqual(result["approval"]["approval_type"], "external_vendor_email")
        self.assertIn("External vendor communication", result["approval"]["risk_reason"])

        logs = self.repo.list_audit_logs(limit=50)
        self.assertGreaterEqual(len(logs), 9)
        logged_actions = {log["action"] for log in logs}
        self.assertTrue(
            {
                "chat.command.received",
                "agent.plan.created",
                "agenda.prepared",
                "meeting.scheduled",
                "reminder.generated",
                "meeting_notes.generated",
                "decisions.extracted",
                "action_items.created",
                "external_email.drafted",
                "approval.queued",
                "dashboard.updated",
                "workflow.completed",
            }.issubset(logged_actions)
        )
        for log in logs:
            self.assertTrue(log["timestamp"])
            self.assertTrue(log["action"])
            self.assertTrue(log["status"])

        queued_logs = [log for log in logs if log["action"] == "external_email.drafted"]
        self.assertEqual(len(queued_logs), 1)
        self.assertTrue(queued_logs[0]["approval_required"])
        self.assertIn("External vendor communication", queued_logs[0]["approval_reason"])

    def test_human_can_edit_then_approve_external_email(self):
        result = self.workflow.run("Plan tomorrow's vendor review meeting.")
        approval_id = result["approval"]["id"]

        edited = self.approvals.decide(
            approval_id,
            action="edit",
            subject="Updated subject",
            body="Edited body for review.",
        )
        self.assertEqual(edited["status"], "pending")
        self.assertEqual(edited["subject"], "Updated subject")

        sent = self.approvals.decide(approval_id, action="approve_send")
        self.assertEqual(sent["status"], "sent")
        self.assertTrue(sent["sent_at"])

        dashboard = self.repo.dashboard()
        self.assertEqual(dashboard["metrics"]["pending_approvals"], 0)

        with self.assertRaises(ValueError):
            self.approvals.decide(
                approval_id,
                action="edit",
                subject="Should not change after send",
            )

    def test_human_can_cancel_external_email(self):
        result = self.workflow.run("Plan tomorrow's vendor review meeting.")
        approval_id = result["approval"]["id"]

        cancelled = self.approvals.decide(
            approval_id,
            action="cancel",
            reason="Needs legal review first.",
        )

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["cancelled_reason"], "Needs legal review first.")
        dashboard = self.repo.dashboard()
        self.assertEqual(dashboard["metrics"]["pending_approvals"], 0)

    def test_policy_requires_human_approval_for_risky_actions(self):
        risky_actions = {
            "external_vendor_email",
            "payment",
            "travel_booking",
            "expense_approval",
            "contract_change",
            "confidential_document_sharing",
            "file_deletion",
            "legal_compliance_decision",
            "emergency_safety_decision",
            "policy_exception",
        }

        for action_type in risky_actions:
            self.assertTrue(requires_approval(action_type))
            self.assertIsNotNone(approval_reason(action_type))
            self.assertFalse(can_auto_execute(action_type))

        for action_type in {
            "calendar_hold",
            "agenda_preparation",
            "internal_reminder",
            "meeting_notes",
            "task_creation",
            "dashboard_update",
        }:
            self.assertFalse(requires_approval(action_type))
            self.assertTrue(can_auto_execute(action_type))

    def test_approval_rules_cover_all_sensitive_approval_types(self):
        rules = ApprovalRulesService()
        cases = {
            "expense_approval": ("expense_management", ["finance_manager", "admin"], "finance_manager"),
            "payment": ("expense_management", ["finance_manager", "admin"], "finance_manager"),
            "invoice_mismatch": ("expense_management", ["finance_manager", "admin"], "finance_manager"),
            "reimbursement": ("expense_management", ["finance_manager", "admin"], "finance_manager"),
            "vendor_followup": ("vendor_management", ["admin"], "admin"),
            "external_vendor_email": ("vendor_management", ["admin"], "admin"),
            "meeting_approval": ("meeting_management", ["admin"], "admin"),
            "vendor_contract_renewal": ("vendor_management", ["admin"], "admin"),
            "vendor_contract_change": ("vendor_management", ["admin"], "admin"),
            "travel_booking": ("travel_management", ["admin"], "admin"),
            "inventory_reorder": ("inventory_management", ["admin"], "admin"),
            "it_equipment_reorder": ("inventory_management", ["it_manager", "admin"], "it_manager"),
            "password_request": ("it_request", ["it_manager", "admin"], "it_manager"),
            "account_access": ("it_request", ["it_manager", "admin"], "it_manager"),
            "device_request": ("it_request", ["it_manager", "admin"], "it_manager"),
            "floor_activity_issue": (
                "floor_activity_management",
                ["admin"],
                "admin",
            ),
            "confidential_document_sharing": ("document_management", ["admin"], "admin"),
            "file_deletion": ("document_management", ["admin"], "admin"),
            "legal_compliance_decision": ("document_management", ["admin"], "admin"),
            "policy_exception": ("document_management", ["admin"], "admin"),
        }

        for approval_type, (task_type, required_roles, assigned_role) in cases.items():
            route = rules.apply_rule(
                task_type="report_generation",
                approval_type=approval_type,
                requester_user_id=42,
            ).to_dict()

            self.assertEqual(route["task_type"], task_type)
            self.assertEqual(route["required_approval_roles"], required_roles)
            self.assertEqual(route["assigned_role"], assigned_role)
            self.assertTrue(route["approval_required"])
            self.assertEqual(route["requester_user_id"], 42)
            self.assertIn("approval", route["required_role_label"].lower())

    def test_approval_rules_route_safe_request_without_approval(self):
        rules = ApprovalRulesService()

        route = rules.route_request(
            message="Create a weekly operations report from mocked dashboard data.",
            requester_user_id=7,
        )

        self.assertEqual(route["task_type"], "report_generation")
        self.assertEqual(route["assigned_role"], "admin")
        self.assertFalse(route["approval_required"])
        self.assertEqual(route["required_approval_roles"], [])
        self.assertEqual(route["status"], "routed")

    def test_inventory_routing_sends_it_equipment_to_it(self):
        rules = ApprovalRulesService()

        route = rules.route_request(
            message="Reorder laptops because IT equipment stock is low.",
            requester_user_id=7,
        )

        self.assertEqual(route["task_type"], "inventory_management")
        self.assertEqual(route["approval_type"], "it_equipment_reorder")
        self.assertEqual(route["assigned_role"], "it_manager")
        self.assertEqual(route["required_approval_roles"], ["it_manager", "admin"])

    def test_inventory_consumables_route_to_admin(self):
        rules = ApprovalRulesService()

        route = rules.route_request(
            message="Order 10 printer cartridges.",
            requester_user_id=7,
        )

        self.assertEqual(route["task_type"], "inventory_management")
        self.assertEqual(route["approval_type"], "inventory_reorder")
        self.assertEqual(route["assigned_role"], "admin")
        self.assertEqual(route["required_approval_roles"], ["admin"])

    def test_route_request_endpoint_persists_and_audits_route(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/requests/route",
            json={"message": "Approve the invoice mismatch for ABC Supplies."},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["route"]["task_type"], "expense_management")
        self.assertEqual(payload["route"]["required_approval_roles"], ["finance_manager", "admin"])
        self.assertEqual(payload["request"]["status"], "pending_approval")
        self.assertTrue(payload["request"]["approval_required"])

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        actions = {log["action"] for log in logs}
        self.assertIn("request.routed", actions)
        self.assertIn("approval.rule.applied", actions)

        dashboard = client.get("/api/dashboard", headers=headers).json()
        self.assertEqual(len(dashboard["routed_requests"]), 1)
        self.assertEqual(dashboard["routed_requests"][0]["required_role_label"], "Requires Finance Manager/Admin approval")

    def test_route_request_endpoint_handles_simple_reminder_without_approval(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/requests/route",
            json={"message": "Remind the team about tomorrow's internal meeting."},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["route"]["task_type"], "meeting_management")
        self.assertFalse(payload["route"]["approval_required"])
        self.assertEqual(payload["route"]["required_approval_roles"], [])

    def test_admin_login_current_user_dashboard_and_tickets_are_available(self):
        client, _ = self.api_client()
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"},
        )
        self.assertEqual(login_response.status_code, 200)
        headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

        me_response = client.get("/api/auth/me", headers=headers)
        dashboard_response = client.get("/api/dashboard", headers=headers)
        tickets_response = client.get("/api/tickets", headers=headers)

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["user"]["email"], "admin@company.com")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("metrics", dashboard_response.json())
        self.assertEqual(tickets_response.status_code, 200)
        self.assertGreaterEqual(len(tickets_response.json()["tickets"]), 8)

    def test_dashboard_charts_are_role_based(self):
        client, _ = self.api_client()
        role_expectations = [
            ("admin@company.com", "admin123", {"tickets_by_status", "tasks_by_status", "expenses_by_month", "inventory_by_status"}),
            ("it@company.com", "it123", {"it_tickets_by_status", "it_tickets_by_category", "inventory_by_status"}),
            ("finance@company.com", "finance123", {"expenses_by_category", "expenses_by_month", "travel_spend_by_month", "vendor_billing"}),
        ]

        for email, password, expected_ids in role_expectations:
            headers = self.auth_headers(client, email, password)
            response = client.get("/api/dashboard", headers=headers)

            self.assertEqual(response.status_code, 200)
            chart_ids = {chart["id"] for chart in response.json()["charts"]}
            self.assertEqual(chart_ids, expected_ids)

        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        employee_response = client.get("/api/dashboard", headers=employee_headers)

        self.assertEqual(employee_response.status_code, 200)
        self.assertEqual(employee_response.json()["charts"], [])

    def test_dashboard_vendor_billing_is_role_scoped(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)

        monthly = client.post(
            "/api/vendors",
            json=self.vendor_payload(vendor_name="Alpha Food", service_provided="Food", billing_amount=1200, billing_cycle="Monthly"),
            headers=admin_headers,
        )
        quarterly = client.post(
            "/api/vendors",
            json=self.vendor_payload(vendor_name="Beta IT", service_provided="IT Services", billing_amount=3000, billing_cycle="Quarterly"),
            headers=admin_headers,
        )
        self.assertEqual(monthly.status_code, 200)
        self.assertEqual(quarterly.status_code, 200)

        admin_dashboard = client.get("/api/dashboard", headers=admin_headers).json()["vendor_billing_dashboard"]
        self.assertTrue(admin_dashboard["can_view_billing"])
        self.assertEqual(admin_dashboard["service_summary"][0]["service"], "Food")
        self.assertEqual(admin_dashboard["service_summary"][0]["count"], 1)
        self.assertEqual(admin_dashboard["current_billing"]["total_monthly_equivalent"], 2200)
        self.assertEqual(len(admin_dashboard["current_billing"]["rows"]), 2)
        self.assertEqual({item["label"] for item in admin_dashboard["expected_billing"]}, {"This month", "Next month", "Current quarter", "Current year"})

        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        finance_dashboard = client.get("/api/dashboard", headers=finance_headers).json()["vendor_billing_dashboard"]
        self.assertTrue(finance_dashboard["can_view_billing"])
        self.assertEqual(finance_dashboard["current_billing"]["total_monthly_equivalent"], 2200)

        it_headers = self.auth_headers(client, "it@company.com", "it123")
        it_dashboard = client.get("/api/dashboard", headers=it_headers).json()["vendor_billing_dashboard"]
        self.assertFalse(it_dashboard["can_view_billing"])
        self.assertEqual(it_dashboard["current_billing"]["rows"], [])
        self.assertEqual([vendor["vendor_name"] for vendor in it_dashboard["current_vendors"]], ["Beta IT"])

        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        employee_dashboard = client.get("/api/dashboard", headers=employee_headers).json()
        self.assertIsNone(employee_dashboard["vendor_billing_dashboard"])

    def test_chatbot_answers_are_role_scoped(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        create_user = client.post(
            "/api/users",
            json={
                "name": "Report Viewer",
                "email": "report.viewer@example.com",
                "password": "viewer123",
                "role": "employee",
            },
            headers=admin_headers,
        )
        create_vendor = client.post(
            "/api/vendors",
            json=self.vendor_payload(vendor_name="Billing Partner", service_provided="Food", billing_amount=2400, billing_cycle="Monthly"),
            headers=admin_headers,
        )
        self.assertEqual(create_user.status_code, 200)
        self.assertEqual(create_vendor.status_code, 200)

        admin_users = client.post("/api/chat/assistant", json={"message": "Show users"}, headers=admin_headers)
        self.assertEqual(admin_users.status_code, 200)
        self.assertIn("admin-created users", admin_users.json()["response"]["message"])
        self.assertEqual(admin_users.json()["source"], "Users")
        self.assertTrue(any("report.viewer@example.com" in item for item in admin_users.json()["response"]["bullets"]))

        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        finance_vendor = client.post("/api/chat/assistant", json={"message": "Show vendor billing"}, headers=finance_headers)
        finance_it_tickets = client.post("/api/chat/assistant", json={"message": "Show IT tickets"}, headers=finance_headers)
        self.assertEqual(finance_vendor.status_code, 200)
        self.assertEqual(finance_vendor.json()["source"], "Vendor billing")
        self.assertIn("monthly equivalent", finance_vendor.json()["response"]["message"].lower())
        self.assertEqual(finance_it_tickets.json()["response"]["message"], "You do not have access to that information.")

        it_headers = self.auth_headers(client, "it@company.com", "it123")
        it_inventory = client.post("/api/chat/assistant", json={"message": "Show inventory in use"}, headers=it_headers)
        it_vendor_billing = client.post("/api/chat/assistant", json={"message": "Show vendor billing"}, headers=it_headers)
        it_expenses = client.post("/api/chat/assistant", json={"message": "Show pending expenses"}, headers=it_headers)
        self.assertIn("inventory", it_inventory.json()["response"]["message"].lower())
        self.assertEqual(it_vendor_billing.json()["response"]["message"], "You do not have access to that information.")
        self.assertEqual(it_expenses.json()["response"]["message"], "You do not have access to that information.")

        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        employee_tickets = client.post("/api/chat/assistant", json={"message": "Show my tickets"}, headers=employee_headers)
        employee_expenses = client.post("/api/chat/assistant", json={"message": "Show expenses"}, headers=employee_headers)
        legacy_route = client.post("/api/chatbot/ask", json={"message": "Show my tickets"}, headers=employee_headers)
        self.assertIn("your", employee_tickets.json()["response"]["message"].lower())
        self.assertEqual(employee_expenses.json()["response"]["message"], "You do not have access to that information.")
        self.assertEqual(legacy_route.status_code, 200)

    def test_chatbot_food_vendor_details_show_contact_and_phone(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        create_vendor = client.post(
            "/api/vendors",
            json=self.vendor_payload(
                vendor_name="Rohit Test Food",
                contact_person="Rohit",
                email="rohit.food@example.com",
                contact_details="43241141324",
                service_provided="Food",
                billing_amount=4322,
                billing_cycle="Quarterly",
                end_date="2026-12-31",
            ),
            headers=admin_headers,
        )
        self.assertEqual(create_vendor.status_code, 200)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "give me details of food vendors"},
            headers=admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertIn("food vendors", payload["answer"])
        self.assertNotIn("Showing first 10", payload["answer"])
        self.assertEqual(payload["bullets"], [])
        table = payload["table"]
        self.assertIn("Contact", table["columns"])
        self.assertIn("Phone", table["columns"])
        self.assertIn("Service", table["columns"])
        self.assertIn("Billing", table["columns"])
        self.assertIn("End Date", table["columns"])
        rohit_row = next(row for row in table["rows"] if row["Vendor Name"] == "Rohit Test Food")
        self.assertEqual(rohit_row["Contact"], "Rohit")
        self.assertEqual(rohit_row["Phone"], "43241141324")
        self.assertEqual(rohit_row["Service"], "Food")
        self.assertEqual(rohit_row["Billing"], "₹4,322 / Q")
        self.assertEqual(rohit_row["End Date"], "31/12/2026")
        self.assertEqual(rohit_row["Status"], "Active")

    def test_chatbot_vendor_details_honors_requested_count(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        vendors_response = client.get("/api/vendors", headers=admin_headers)
        self.assertEqual(vendors_response.status_code, 200)
        existing_count = len(vendors_response.json()["vendors"])
        for index in range(existing_count + 1, 27):
            created = client.post(
                "/api/vendors",
                json=self.vendor_payload(
                    vendor_name=f"Requested Count Vendor {index}",
                    contact_person=f"Contact {index}",
                    email=f"requested.vendor.{index}@example.com",
                    contact_details=f"90000000{index:02d}",
                    service_provided="Office Supplies",
                    billing_amount=1000 + index,
                    billing_cycle="Monthly",
                    end_date="2026-12-31",
                ),
                headers=admin_headers,
            )
            self.assertEqual(created.status_code, 200)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "give me 26 vendors details"},
            headers=admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertIn("I found", payload["answer"])
        self.assertNotIn("Showing first 10", payload["answer"])
        self.assertEqual(payload["bullets"], [])
        table = payload["table"]
        self.assertEqual(len(table["rows"]), 26)
        for column in ["Vendor Name", "Service", "Contact", "Phone", "Billing", "End Date", "Status"]:
            self.assertIn(column, table["columns"])

    def test_chatbot_employee_can_create_ticket_from_natural_language(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/chat/assistant",
            json={"message": "create ticket for me laptop not working"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Ticket agent")
        self.assertIn("Created ticket", payload["answer"])
        self.assertTrue(payload["created_record_id"].startswith("IT-"))
        self.assertEqual(payload["table"]["rows"][0]["Status"], "Open")

        tickets = client.get("/api/tickets", headers=headers).json()["tickets"]
        created = next(ticket for ticket in tickets if ticket["ticket_id"] == payload["created_record_id"])
        self.assertEqual(created["requester_email"], "employee@company.com")
        self.assertEqual(created["ticket_type"], "IT")
        self.assertEqual(created["category"], "Device")

    def test_chatbot_answers_today_date_utility_question(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "what todays date"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Date and time")
        self.assertRegex(payload["answer"], r"Today's date is \d{2}/\d{2}/\d{4}\.")

    def test_chatbot_calendar_events_are_not_confused_with_today_date(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "can you show me calendar events"},
            headers=headers,
        )
        typo_response = client.post(
            "/api/chat/assistant",
            json={"message": "show calender events"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Calendar events")
        self.assertEqual(payload["answer"], "Here are calendar events:")
        self.assertIn("table", payload)
        self.assertGreaterEqual(len(payload["table"]["rows"]), 3)
        self.assertNotIn("Today's date", payload["answer"])

        self.assertEqual(typo_response.status_code, 200)
        typo_payload = typo_response.json()["response"]
        self.assertEqual(typo_payload["source"], "Calendar events")
        self.assertIn("table", typo_payload)

    def test_chatbot_intent_priority_overrides_bad_external_date_for_calendar(self):
        with (
            patch.object(settings, "ai_provider", "deepinfra"),
            patch.object(settings, "deepinfra_api_key", "df-" + ("x" * 32)),
            patch.object(DeepInfraChatClient, "classify_intent", return_value={"intent": "utility_date", "confidence": 0.99, "entities": {}}),
            patch.object(DeepInfraChatClient, "refine_response", side_effect=RuntimeError("skip external refine")),
        ):
            client, _ = self.api_client()
            headers = self.auth_headers(client)
            response = client.post(
                "/api/chat/assistant",
                json={"message": "can you show me calendar events"},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Calendar events")
        self.assertEqual(payload["answer"], "Here are calendar events:")

    def test_chatbot_vendor_count_request(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "how many vendors do we have?"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Vendors")
        self.assertIn("active vendors", payload["answer"])
        self.assertRegex(payload["answer"], r"You have \d+ active vendors visible for your access level\.")

    def test_chatbot_understands_misspelled_vendor_details(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        create_vendor = client.post(
            "/api/vendors",
            json=self.vendor_payload(
                vendor_name="Typo Food Vendor",
                contact_person="Tyra",
                email="typo.food@example.com",
                contact_details="9876500012",
                service_provided="Food",
                billing_amount=7000,
                billing_cycle="Monthly",
                end_date="2026-12-31",
            ),
            headers=admin_headers,
        )
        self.assertEqual(create_vendor.status_code, 200)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "give me food vendor deatils"},
            headers=admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Vendors")
        self.assertEqual(payload["bullets"], [])
        typo_row = next(row for row in payload["table"]["rows"] if row["Vendor Name"] == "Typo Food Vendor")
        self.assertEqual(typo_row["Contact"], "Tyra")
        self.assertEqual(typo_row["Phone"], "9876500012")

    def test_chatbot_understands_misspelled_recent_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "shoe me recent tikets"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Tickets")
        self.assertEqual(payload["answer"], "Here are recent tickets:")
        self.assertTrue(payload["bullets"])

    def test_chatbot_ticket_history_includes_past_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={"message": "can you give me ticket history"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Tickets")
        self.assertEqual(payload["answer"], "Here is your ticket history:")
        statuses = {row["Status"] for row in payload["table"]["rows"]}
        self.assertTrue({"Resolved", "Open"}.intersection(statuses))

    def test_chatbot_uses_previous_ticket_context_for_earlier_history(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/chat/assistant",
            json={
                "message": "I am not talking about. I want earlier history",
                "history": [
                    {"role": "user", "text": "can you give me ticket history"},
                    {"role": "assistant", "text": "Here is your ticket history:", "source": "Tickets"},
                ],
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Tickets")
        self.assertEqual(payload["answer"], "Here is your ticket history:")
        self.assertIn("table", payload)

    def test_chatbot_understands_misspelled_ticket_creation(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/chat/assistant",
            json={"message": "create tikcet for laptop issue"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Ticket agent")
        self.assertTrue(payload["created_record_id"].startswith("IT-"))

    def test_chatbot_deepinfra_failure_falls_back_to_local_intent(self):
        with (
            patch.object(settings, "ai_provider", "deepinfra"),
            patch.object(settings, "deepinfra_api_key", "df-" + ("x" * 32)),
            patch.object(DeepInfraChatClient, "classify_intent", side_effect=RuntimeError("DeepInfra unavailable")),
            patch.object(DeepInfraChatClient, "refine_response", side_effect=RuntimeError("DeepInfra unavailable")),
        ):
            client, _ = self.api_client()
            headers = self.auth_headers(client)
            response = client.post(
                "/api/chat/assistant",
                json={"message": "sho me recent tickets"},
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Tickets")
        self.assertEqual(payload["answer"], "Here are recent tickets:")

    def test_chatbot_employee_ticket_status_is_scoped_to_own_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        own_response = client.post(
            "/api/chat/assistant",
            json={"message": "what is the status of my ticket IT-1001?"},
            headers=headers,
        )
        other_response = client.post(
            "/api/chat/assistant",
            json={"message": "what is the status of ticket IT-1003?"},
            headers=headers,
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.json()["response"]["table"]["rows"][0]["Ticket ID"], "IT-1001")
        self.assertIn("currently", own_response.json()["response"]["answer"])
        self.assertEqual(other_response.json()["response"]["answer"], "I could not find that ticket for your access level.")

    def test_chatbot_ticket_status_update_requires_confirmation(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        request = client.post(
            "/api/chat/assistant",
            json={"message": "resolve ticket IT-1001"},
            headers=headers,
        )

        self.assertEqual(request.status_code, 200)
        payload = request.json()["response"]
        self.assertTrue(payload["confirmation_required"])
        self.assertEqual(payload["action"]["type"], "update_ticket_status")
        self.assertEqual(payload["action"]["payload"]["ticket_id"], "IT-1001")
        self.assertEqual(payload["action"]["payload"]["status"], "Resolved")

        confirm = client.post(
            "/api/chat/assistant",
            json={"message": "Confirm", "action": payload["action"]},
            headers=headers,
        )

        self.assertEqual(confirm.status_code, 200)
        confirmed = confirm.json()["response"]
        self.assertIn("Confirmed and updated IT-1001 to Resolved", confirmed["answer"])
        self.assertEqual(confirmed["table"]["rows"][0]["Status"], "Resolved")

    def test_chatbot_it_manager_last_5_inventory_updates(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "it@company.com", "it123")

        response = client.post(
            "/api/chat/assistant",
            json={"message": "give last 5 inventory updates"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Inventory")
        self.assertEqual(payload["answer"], "Here are the last 5 inventory updates:")
        self.assertLessEqual(len(payload["table"]["rows"]), 5)
        self.assertIn("Serial No.", payload["table"]["columns"])

    def test_chatbot_finance_manager_expenses_month_wise(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.post(
            "/api/chat/assistant",
            json={"message": "tell me expenses month wise"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["response"]
        self.assertEqual(payload["source"], "Expenses")
        self.assertEqual(payload["answer"], "Here are the month-wise expense totals:")
        self.assertIn("Month", payload["table"]["columns"])
        self.assertIn("Total", payload["table"]["columns"])

    def test_chatbot_finance_manager_expenses_by_category_and_pending(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        by_category = client.post(
            "/api/chat/assistant",
            json={"message": "show expense by category"},
            headers=headers,
        )
        pending = client.post(
            "/api/chat/assistant",
            json={"message": "show pending expenses"},
            headers=headers,
        )

        self.assertEqual(by_category.status_code, 200)
        category_payload = by_category.json()["response"]
        self.assertEqual(category_payload["source"], "Expenses")
        self.assertEqual(category_payload["answer"], "Here are expenses by category:")
        self.assertIn("Category", category_payload["table"]["columns"])
        self.assertIn("Total", category_payload["table"]["columns"])

        self.assertEqual(pending.status_code, 200)
        pending_payload = pending.json()["response"]
        self.assertEqual(pending_payload["source"], "Expenses")
        self.assertIn("pending", pending_payload["answer"].lower())
        self.assertIn("Expense", pending_payload["table"]["columns"])
        self.assertIn("Amount", pending_payload["table"]["columns"])

    def test_chatbot_action_agent_blocks_unauthorized_request(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/chat/assistant",
            json={"message": "how much expenses happened last month?"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"]["answer"], "You do not have access to that information.")

    def test_mock_email_send_creates_communication_log(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)

        response = client.post(
            "/api/communications/send-email",
            json={
                "recipient_name": "Rahul",
                "recipient_email": "rahul@example.com",
                "recipient_phone": "",
                "subject": "Vendor billing reminder",
                "message_body": "Please review the attached vendor bill.",
                "related_module": "vendors",
                "related_record_id": "vendor-123",
                "channel": "email",
            },
            headers=admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Mock message sent")
        log = response.json()["logs"][0]
        self.assertEqual(log["channel"], "email")
        self.assertEqual(log["recipient_email"], "rahul@example.com")
        self.assertEqual(log["status"], "mock_sent")
        logs = client.get("/api/communications/logs", headers=admin_headers)
        self.assertTrue(any(item["id"] == log["id"] for item in logs.json()["logs"]))

    def test_mock_whatsapp_send_creates_communication_log(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)

        response = client.post(
            "/api/communications/send-whatsapp",
            json={
                "recipient_name": "Rahul",
                "recipient_email": "",
                "recipient_phone": "+919876543210",
                "subject": "Ticket update",
                "message_body": "Your ticket has been resolved.",
                "related_module": "tickets",
                "related_record_id": "IT-1001",
                "channel": "whatsapp",
            },
            headers=admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Mock message sent")
        log = response.json()["logs"][0]
        self.assertEqual(log["channel"], "whatsapp")
        self.assertEqual(log["recipient_phone"], "+919876543210")
        self.assertEqual(log["status"], "mock_sent")

    def test_all_roles_can_manage_their_own_connectors(self):
        client, _ = self.api_client()
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        finance_list = client.get("/api/connectors", headers=finance_headers)
        self.assertEqual(finance_list.status_code, 200)
        self.assertEqual({item["connector_type"] for item in finance_list.json()["connectors"]}, {"email", "whatsapp"})

        configured = client.post(
            "/api/connectors/email/configure",
            json={
                "provider": "SMTP",
                "from_name": "Finance Desk",
                "from_email": "finance@company.com",
                "smtp_host": "smtp.example.test",
                "smtp_port": 587,
                "smtp_username": "finance-user",
                "smtp_password": "not-stored-in-plain-response",
                "sendgrid_api_key": "",
                "reply_to_email": "finance@company.com",
            },
            headers=finance_headers,
        )
        self.assertEqual(configured.status_code, 200)
        self.assertEqual(configured.json()["connector"]["provider"], "SMTP")
        self.assertTrue(configured.json()["connector"]["config"]["has_smtp_password"])
        self.assertNotIn("smtp_password", configured.json()["connector"]["config"])

        it_list = client.get("/api/connectors", headers=it_headers)
        self.assertEqual(it_list.status_code, 200)
        it_email = next(item for item in it_list.json()["connectors"] if item["connector_type"] == "email")
        self.assertEqual(it_email["provider"], "Mock Email")
        self.assertEqual(it_email["status"], "mock_mode")
        self.assertNotEqual(it_email.get("user_id"), configured.json()["connector"]["user_id"])

        employee_test = client.post("/api/connectors/email/test", headers=employee_headers)
        self.assertEqual(employee_test.status_code, 200)
        self.assertEqual(employee_test.json()["logs"][0]["recipient_email"], "employee@company.com")

        employee_send_test = client.post(
            "/api/communications/send-email",
            json={
                "recipient_name": "Employee User",
                "recipient_email": "employee@company.com",
                "subject": "Connector send test",
                "message_body": "Testing my own connector.",
                "related_module": "settings",
                "related_record_id": "employee-email-test",
                "channel": "email",
            },
            headers=employee_headers,
        )
        self.assertEqual(employee_send_test.status_code, 200)

    def test_google_email_start_reports_missing_oauth_config(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        with patch.object(settings, "google_client_id", ""), patch.object(settings, "google_client_secret", ""), patch.object(settings, "google_redirect_uri", ""):
            response = client.get("/api/connectors/google/start", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["configured"])
        self.assertEqual(response.json()["message"], "Google email connection is not configured yet.")

    def test_google_email_start_returns_authorization_url_when_configured(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        with patch.object(settings, "google_client_id", "client-id"), patch.object(settings, "google_client_secret", "secret"), patch.object(settings, "google_redirect_uri", "http://127.0.0.1:8000/api/connectors/google/callback"):
            response = client.get("/api/connectors/google/start", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["configured"])
        authorization_url = response.json()["authorization_url"]
        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", authorization_url)
        self.assertIn("gmail.send", authorization_url)

    def test_gmail_connector_tokens_are_not_exposed(self):
        client, app = self.api_client()
        headers = self.auth_headers(client)
        admin_user = app.state.repository.get_user_by_email("admin@company.com")
        app.state.repository.upsert_connector(
            admin_user["id"],
            "email",
            "Gmail",
            "connected",
            "Email",
            {
                "connected_email": "admin@gmail.com",
                "connected_at": "2026-05-12T08:00:00+00:00",
                "access_token": "secret-access-token",
                "refresh_token": "secret-refresh-token",
                "id_token": "secret-id-token",
            },
        )

        response = client.get("/api/connectors", headers=headers)

        self.assertEqual(response.status_code, 200)
        email_connector = next(item for item in response.json()["connectors"] if item["connector_type"] == "email")
        self.assertEqual(email_connector["provider"], "Gmail")
        self.assertEqual(email_connector["status"], "connected")
        self.assertEqual(email_connector["config"]["connected_email"], "admin@gmail.com")
        self.assertTrue(email_connector["config"]["has_google_access_token"])
        self.assertNotIn("access_token", email_connector["config"])
        self.assertNotIn("refresh_token", email_connector["config"])
        self.assertNotIn("id_token", email_connector["config"])

    def test_google_configured_email_send_requires_connected_gmail(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        with patch.object(settings, "google_client_id", "client-id"), patch.object(settings, "google_client_secret", "secret"), patch.object(settings, "google_redirect_uri", "http://127.0.0.1:8000/api/connectors/google/callback"):
            response = client.post(
                "/api/communications/send-email",
                json={
                    "recipient_name": "Rahul",
                    "recipient_email": "rahul@example.com",
                    "subject": "Gmail required",
                    "message_body": "Please review.",
                    "related_module": "settings",
                    "related_record_id": "gmail-required",
                    "channel": "email",
                },
                headers=headers,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Please connect your email in Settings first.")

    def test_send_uses_current_user_connector_and_role_permissions(self):
        client, _ = self.api_client()
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        configured = client.post(
            "/api/connectors/email/configure",
            json={"provider": "SMTP", "from_name": "Finance Desk", "from_email": "finance@company.com"},
            headers=finance_headers,
        )
        self.assertEqual(configured.status_code, 200)

        sent = client.post(
            "/api/communications/send-email",
            json={
                "recipient_name": "Vendor",
                "recipient_email": "vendor@example.com",
                "subject": "Vendor billing reminder",
                "message_body": "Please review the billing reminder.",
                "related_module": "vendors",
                "related_record_id": "vendor-42",
                "channel": "email",
            },
            headers=finance_headers,
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.json()["logs"][0]["provider"], "SMTP")
        self.assertEqual(sent.json()["logs"][0]["status"], "mock_sent")

        blocked = client.post(
            "/api/communications/send-email",
            json={
                "recipient_name": "Vendor",
                "recipient_email": "vendor@example.com",
                "subject": "Vendor billing reminder",
                "message_body": "Please review the billing reminder.",
                "related_module": "vendors",
                "related_record_id": "vendor-42",
                "channel": "email",
            },
            headers=it_headers,
        )
        self.assertEqual(blocked.status_code, 403)

    def test_chatbot_pending_approvals_uses_clear_empty_and_list_responses(self):
        client, app = self.api_client()
        admin_headers = self.auth_headers(client)

        empty_response = client.post("/api/chat/assistant", json={"message": "Show pending approvals"}, headers=admin_headers)
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["answer"], "You don’t have any pending approvals right now.")
        self.assertEqual(empty_response.json()["source"], "Approvals")

        self.add_mock_approval(app, "expense_approval")
        list_response = client.post("/api/chat/assistant", json={"message": "Show pending approvals"}, headers=admin_headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["answer"], "Here are your pending approvals:")
        self.assertTrue(any("expense_approval request" in item for item in list_response.json()["bullets"]))
        self.assertTrue(any("Requested by Internal Reviewer" in item for item in list_response.json()["bullets"]))

    def test_chatbot_understands_fuzzy_intents(self):
        client, app = self.api_client()
        admin_headers = self.auth_headers(client)
        self.add_mock_approval(app, "expense_approval")
        created_vendor = client.post(
            "/api/vendors",
            json=self.vendor_payload(vendor_name="Fuzzy Billing Partner", service_provided="Food", billing_amount=1800, billing_cycle="Monthly"),
            headers=admin_headers,
        )
        self.assertEqual(created_vendor.status_code, 200)

        test_cases = [
            ("shoe me recent tickets", "Here are recent tickets:", "Tickets"),
            ("show Recent tickets", "Here are recent tickets:", "Tickets"),
            ("sho me opentask", "open visible tasks", "Tasks"),
            ("show panding approvals", "Here are your pending approvals:", "Approvals"),
            ("venor billing", "Total current monthly equivalent vendor billing", "Vendor billing"),
            ("expence this month", "expenses total", "Expenses"),
            ("inventry summery", "inventory items match", "Inventory"),
            ("what’s your name", "I’m Conci AI", "Conci AI"),
        ]
        for message, expected_text, expected_source in test_cases:
            with self.subTest(message=message):
                response = client.post("/api/chat/assistant", json={"message": message}, headers=admin_headers)
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected_text.lower(), response.json()["answer"].lower())
                self.assertEqual(response.json()["source"], expected_source)

    def test_chatbot_answers_casual_questions(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        test_cases = [
            ("what’s your name?", "I’m Conci AI, your assistant for admin, IT, finance, and employee workflows."),
            ("who are you?", "I’m Conci AI, your smart concierge"),
            ("hi", "Hi! How can I help you today?"),
            ("what can you do?", "based on your access"),
            ("are you male or female?", "I don’t have a gender. I’m Conci AI, your digital concierge assistant."),
            ("are you a boy or girl?", "Neither. I’m Conci AI, an AI assistant here to help with your work."),
            ("what is your gender?", "I don’t have a gender."),
            ("are you human?", "No, I’m an AI assistant."),
            ("are you real?", "I’m real as software, but I’m not a person."),
            ("who made you?", "built into Agent Concierge"),
        ]
        for message, expected in test_cases:
            with self.subTest(message=message):
                response = client.post("/api/chat/assistant", json={"message": message}, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.json()["answer"])
                self.assertEqual(response.json()["source"], "Conci AI")

        fallback = client.post("/api/chat/assistant", json={"message": "can you make coffee"}, headers=headers)
        self.assertEqual(
            fallback.json()["answer"],
            "I’m not sure what you mean. You can ask me about tickets, tasks, approvals, vendors, inventory, expenses, travel, or reports.",
        )

    def test_chatbot_reads_attached_csv_file(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = (
            "Employee Name,Serial No.,Model No.,RAM,Disk,Location,Status,Notes\n"
            "Priya Shah,SN-1001,Latitude 5420,16GB,512GB SSD,Pune,In Use,Primary laptop\n"
            "Rohit K,SN-1002,ThinkPad T14,16GB,1TB SSD,Mumbai,Extra,Spare laptop\n"
        ).encode("utf-8")

        response = client.post(
            "/api/chat/assistant",
            data={"message": "can you read the above file"},
            files={"file": ("inventory.csv", csv_content, "text/csv")},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Yes, I can read this file", payload["answer"])
        self.assertIn("2 rows", payload["answer"])
        self.assertIn("Employee Name", payload["answer"])
        self.assertEqual(payload["source"], "Attached file · inventory.csv")
        self.assertFalse("I’m not sure what you mean" in payload["answer"])

    def test_chatbot_reads_attached_xlsx_file_and_answers_row_count(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        rows = [
            ["Employee Name", "Serial No.", "Model No.", "RAM", "Disk", "Location", "Status", "Notes"],
            ["Asha Rao", "SN-2001", "MacBook Air", "16GB", "512GB SSD", "Pune", "In Use", "Design"],
            ["Kabir Sen", "SN-2002", "Dell 7420", "32GB", "1TB SSD", "Delhi", "Submitted to Vendor", "Repair"],
            ["Mira Das", "SN-2003", "HP EliteBook", "16GB", "512GB SSD", "Mumbai", "Extra", "Spare"],
        ]

        response = client.post(
            "/api/chat/assistant",
            data={"message": "how many rows are in this file"},
            files={"file": ("inventory.xlsx", self.make_xlsx(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["answer"], "This XLSX file has 3 data rows.")
        self.assertTrue(any("Employee Name" in bullet for bullet in payload["bullets"]))
        self.assertEqual(payload["source"], "Attached file · inventory.xlsx")

    def test_tickets_endpoint_lists_seeded_it_and_admin_tickets_for_admin(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.get("/api/tickets", headers=headers)

        self.assertEqual(response.status_code, 200)
        tickets = response.json()["tickets"]
        self.assertEqual(len(tickets), 8)
        ticket_types = {ticket["ticket_type"] for ticket in tickets}
        self.assertEqual(ticket_types, {"IT", "Admin"})
        self.assertTrue(any(ticket["ticket_id"] == "IT-1001" for ticket in tickets))
        self.assertTrue(any(ticket["ticket_id"] == "ADM-1001" for ticket in tickets))

    def test_employee_can_create_ticket_and_only_view_own_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        created = client.post("/api/tickets", json=self.ticket_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        ticket = created.json()["ticket"]
        self.assertEqual(ticket["requester_email"], "employee@company.com")
        self.assertEqual(ticket["requester_role"], "employee")
        self.assertEqual(ticket["assigned_role"], "it_manager")

        response = client.get("/api/tickets", headers=headers)
        self.assertEqual(response.status_code, 200)
        tickets = response.json()["tickets"]
        self.assertTrue(tickets)
        self.assertTrue(all(item["requester_email"] == "employee@company.com" for item in tickets))

        status_update = client.patch(
            f"/api/tickets/{ticket['id']}/status",
            json={"status": "Resolved"},
            headers=headers,
        )
        self.assertEqual(status_update.status_code, 403)

    def test_employee_can_create_admin_ticket_with_optional_due_date(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        created = client.post(
            "/api/tickets",
            json=self.ticket_payload(
                ticket_type="Admin",
                title="Book a huddle room",
                description="Please book a small room for tomorrow's project sync.",
                category="Meeting Support",
                due_date=None,
                approval_required=False,
            ),
            headers=headers,
        )

        self.assertEqual(created.status_code, 200)
        ticket = created.json()["ticket"]
        self.assertEqual(ticket["ticket_type"], "Admin")
        self.assertEqual(ticket["assigned_role"], "admin")
        self.assertEqual(ticket["due_date"], "")
        self.assertEqual(ticket["status"], "Open")

    def test_employee_ticket_create_accepts_type_alias(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")
        payload = self.ticket_payload()
        payload["type"] = payload.pop("ticket_type")

        response = client.post("/api/tickets", json=payload, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticket"]["ticket_type"], "IT")

    def test_ticket_create_missing_required_fields_fails_with_clear_error(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")
        payload = self.ticket_payload(title="", description="")

        response = client.post("/api/tickets", json=payload, headers=headers)

        self.assertEqual(response.status_code, 422)
        messages = " ".join(item["msg"] for item in response.json()["detail"])
        self.assertIn("at least 3 characters", messages)

    def test_ticket_creation_records_audit_log(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        created = client.post("/api/tickets", json=self.ticket_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        ticket = created.json()["ticket"]

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        ticket_log = next(log for log in logs if log["action"] == "ticket.created")
        self.assertEqual(ticket_log["actor"], "employee@company.com")
        self.assertEqual(ticket_log["details"]["ticket_id"], ticket["ticket_id"])
        self.assertEqual(ticket_log["details"]["actor_role"], "employee")
        self.assertTrue(ticket_log["approval_required"])

    def test_creating_ticket_creates_notification(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        admin_headers = self.auth_headers(client)

        created = client.post(
            "/api/tickets",
            json=self.ticket_payload(title="Laptop password reset"),
            headers=employee_headers,
        )
        self.assertEqual(created.status_code, 200)
        ticket = created.json()["ticket"]

        employee_notifications = client.get("/api/notifications", headers=employee_headers)
        admin_notifications = client.get("/api/notifications", headers=admin_headers)

        self.assertEqual(employee_notifications.status_code, 200)
        self.assertEqual(admin_notifications.status_code, 200)
        employee_item = next(
            item for item in employee_notifications.json()["notifications"]
            if item["related_entity_id"] == str(ticket["id"])
        )
        admin_item = next(
            item for item in admin_notifications.json()["notifications"]
            if item["related_entity_id"] == str(ticket["id"])
        )
        self.assertEqual(employee_item["title"], "New ticket created")
        self.assertEqual(employee_item["message"], "New ticket created: Laptop password reset")
        self.assertTrue(employee_item["unread"])
        self.assertEqual(admin_item["related_entity_type"], "ticket")

    def test_resolving_ticket_creates_notification(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        created = client.post(
            "/api/tickets",
            json=self.ticket_payload(title="Laptop password reset"),
            headers=employee_headers,
        )
        ticket = created.json()["ticket"]

        resolved = client.patch(
            f"/api/tickets/{ticket['id']}/status",
            json={"status": "Resolved"},
            headers=it_headers,
        )
        self.assertEqual(resolved.status_code, 200)

        notifications = client.get("/api/notifications", headers=employee_headers).json()["notifications"]
        resolved_notification = next(item for item in notifications if item["type"] == "ticket.resolved")
        self.assertEqual(resolved_notification["message"], "Ticket resolved: Laptop password reset")
        self.assertEqual(resolved_notification["related_entity_id"], str(ticket["id"]))

    def test_employee_sees_only_own_ticket_notifications(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        admin_headers = self.auth_headers(client)

        own_ticket = client.post(
            "/api/tickets",
            json=self.ticket_payload(title="Employee VPN access"),
            headers=employee_headers,
        ).json()["ticket"]
        other_ticket = client.post(
            "/api/tickets",
            json=self.ticket_payload(title="Admin-only device request"),
            headers=admin_headers,
        ).json()["ticket"]

        employee_notifications = client.get("/api/notifications", headers=employee_headers).json()["notifications"]
        related_ids = {item["related_entity_id"] for item in employee_notifications}

        self.assertIn(str(own_ticket["id"]), related_ids)
        self.assertNotIn(str(other_ticket["id"]), related_ids)

    def test_mark_notification_as_read_updates_unread_count(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        client.post(
            "/api/tickets",
            json=self.ticket_payload(title="Need printer help"),
            headers=employee_headers,
        )
        before = client.get("/api/notifications", headers=employee_headers).json()
        notification_id = before["notifications"][0]["id"]
        self.assertGreaterEqual(before["unread_count"], 1)

        marked = client.patch(f"/api/notifications/{notification_id}/read", headers=employee_headers)
        after = client.get("/api/notifications", headers=employee_headers).json()

        self.assertEqual(marked.status_code, 200)
        self.assertFalse(marked.json()["notification"]["unread"])
        self.assertEqual(after["unread_count"], before["unread_count"] - 1)

    def test_mark_all_notifications_as_read(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        client.post("/api/tickets", json=self.ticket_payload(title="First ticket"), headers=employee_headers)
        client.post("/api/tickets", json=self.ticket_payload(title="Second ticket"), headers=employee_headers)

        response = client.patch("/api/notifications/read-all", headers=employee_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 0)
        self.assertTrue(all(not item["unread"] for item in response.json()["notifications"]))

    def test_admin_can_create_edit_status_and_delete_task_with_audit_logs(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        created = client.post("/api/tasks", json=self.task_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        task = created.json()["task"]
        self.assertEqual(task["task_id"], "TASK-1006")
        self.assertEqual(task["created_by_email"], "admin@company.com")

        updated = client.put(
            f"/api/tasks/{task['id']}",
            json=self.task_payload(title="Prepare asset handover updated", priority="High"),
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["task"]["priority"], "High")

        status = client.patch(
            f"/api/tasks/{task['id']}/status",
            json={"status": "Completed"},
            headers=headers,
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["task"]["status"], "Completed")

        deleted = client.delete(f"/api/tasks/{task['id']}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["task"]["task_id"], task["task_id"])

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        actions = [log["action"] for log in logs]
        self.assertIn("task.created", actions)
        self.assertIn("task.updated", actions)
        self.assertIn("task.status_changed", actions)
        self.assertIn("task.deleted", actions)

    def test_task_role_scoping_for_admin_it_finance_and_employee(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        admin_tasks = client.get("/api/tasks", headers=admin_headers).json()["tasks"]
        self.assertGreaterEqual(len(admin_tasks), 5)

        it_tasks = client.get("/api/tasks", headers=it_headers).json()["tasks"]
        self.assertTrue(it_tasks)
        self.assertTrue(all(task["department"] == "IT" or task["category"] == "IT" or task["assigned_role"] == "it_manager" for task in it_tasks))

        finance_tasks = client.get("/api/tasks", headers=finance_headers).json()["tasks"]
        self.assertTrue(finance_tasks)
        self.assertTrue(all(task["department"] == "Finance" or task["category"] in {"Finance", "Expense"} or task["assigned_role"] == "finance_manager" for task in finance_tasks))

        employee_created = client.post(
            "/api/tasks",
            json=self.task_payload(
                title="Need admin desk support",
                description="Please help move the visitor desk checklist to the new template.",
                category="Admin",
                department="Admin",
                assigned_to="Employee User",
                assigned_role="employee",
            ),
            headers=employee_headers,
        )
        self.assertEqual(employee_created.status_code, 200)
        employee_task = employee_created.json()["task"]
        employee_tasks = client.get("/api/tasks", headers=employee_headers).json()["tasks"]
        self.assertIn(employee_task["id"], {task["id"] for task in employee_tasks})
        self.assertTrue(
            all(
                task["created_by_email"] == "employee@company.com" or task["assigned_to"] in {"Employee User", "employee@company.com"}
                for task in employee_tasks
            )
        )

        admin_only_task = next(task for task in admin_tasks if task["department"] == "Admin" and task["assigned_role"] == "admin")
        blocked = client.patch(
            f"/api/tasks/{admin_only_task['id']}/status",
            json={"status": "Completed"},
            headers=it_headers,
        )
        self.assertEqual(blocked.status_code, 403)

        employee_blocked = client.put(
            f"/api/tasks/{admin_only_task['id']}",
            json=self.task_payload(category="Admin", department="Admin", assigned_to="Admin User", assigned_role="admin"),
            headers=employee_headers,
        )
        self.assertEqual(employee_blocked.status_code, 403)

    def test_assignable_users_are_role_scoped(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        admin_users = client.get("/api/users/assignable", headers=admin_headers)
        self.assertEqual(admin_users.status_code, 200)
        self.assertGreaterEqual(len(admin_users.json()["users"]), 4)

        it_users = client.get("/api/users/assignable", headers=it_headers).json()["users"]
        self.assertTrue(it_users)
        self.assertTrue(all(user["role"] == "it_manager" for user in it_users))

        finance_users = client.get("/api/users/assignable", headers=finance_headers).json()["users"]
        self.assertTrue(finance_users)
        self.assertTrue(all(user["role"] == "finance_manager" for user in finance_users))

        employee_users = client.get("/api/users/assignable", headers=employee_headers).json()["users"]
        self.assertEqual(len(employee_users), 1)
        self.assertEqual(employee_users[0]["email"], "employee@company.com")

    def test_task_assignment_to_user_creates_notification(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        assignable = client.get("/api/users/assignable", headers=admin_headers).json()["users"]
        employee = next(user for user in assignable if user["email"] == "employee@company.com")

        created = client.post(
            "/api/tasks",
            json=self.task_payload(
                title="Review welcome checklist",
                description="Review the employee welcome checklist before onboarding.",
                category="Admin",
                department="Admin",
                assigned_user_id=employee["id"],
                assigned_to="",
                assigned_email="",
                assigned_role="employee",
            ),
            headers=admin_headers,
        )
        self.assertEqual(created.status_code, 200)
        task = created.json()["task"]
        self.assertEqual(task["assigned_user_id"], employee["id"])
        self.assertEqual(task["assigned_to"], "Employee User")
        self.assertEqual(task["assigned_email"], "employee@company.com")

        notifications = client.get("/api/notifications", headers=employee_headers)
        self.assertEqual(notifications.status_code, 200)
        task_notifications = [
            item for item in notifications.json()["notifications"]
            if item["type"] == "task.assigned" and item["related_entity_id"] == str(task["id"])
        ]
        self.assertTrue(task_notifications)
        self.assertIn("New task assigned: Review welcome checklist", task_notifications[0]["message"])
        self.assertGreaterEqual(notifications.json()["unread_count"], 1)

    def test_employee_cannot_assign_task_to_another_user(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        admin_user = next(
            user for user in client.get("/api/users/assignable", headers=self.auth_headers(client)).json()["users"]
            if user["email"] == "admin@company.com"
        )

        response = client.post(
            "/api/tasks",
            json=self.task_payload(
                title="Assign outside self",
                description="Employee should not assign this to admin.",
                assigned_user_id=admin_user["id"],
            ),
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_task_validation_rejects_missing_required_fields(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")
        payload = self.task_payload(title="", description="")

        response = client.post("/api/tasks", json=payload, headers=headers)

        self.assertEqual(response.status_code, 422)
        messages = " ".join(item["msg"] for item in response.json()["detail"])
        self.assertIn("at least 3 characters", messages)

    def test_legacy_ticket_table_without_requester_role_is_migrated(self):
        db_path = Path(self.tmp.name) / "legacy_ticket.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL UNIQUE,
                    ticket_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requester_user_id INTEGER,
                    requester_name TEXT NOT NULL,
                    requester_email TEXT NOT NULL,
                    assigned_role TEXT NOT NULL,
                    assigned_team TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO tickets (
                    ticket_id, ticket_type, title, description, category, priority,
                    status, requester_user_id, requester_name, requester_email,
                    assigned_role, assigned_team, due_date, approval_required,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "IT-9999",
                    "IT",
                    "Legacy ticket",
                    "Legacy ticket description",
                    "Password",
                    "Medium",
                    "Open",
                    None,
                    "Legacy User",
                    "legacy@example.com",
                    "it_manager",
                    "IT Service Desk",
                    "",
                    0,
                    "2026-05-01T00:00:00+00:00",
                    "2026-05-01T00:00:00+00:00",
                ),
            )

        repo = AdminRepository(db_path)
        tickets = repo.list_tickets()

        self.assertEqual(tickets[0]["requester_role"], "")

    def test_it_manager_can_manage_it_tickets_but_not_admin_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "it@company.com", "it123")
        tickets = client.get("/api/tickets", headers=headers).json()["tickets"]
        it_ticket = self.find_ticket(tickets, "IT-1001")
        ticket_ids = {ticket["ticket_id"] for ticket in tickets}
        self.assertTrue(ticket_ids)
        self.assertTrue(all(ticket_id.startswith("IT-") for ticket_id in ticket_ids))
        admin_headers = self.auth_headers(client)
        admin_ticket = self.find_ticket(client.get("/api/tickets", headers=admin_headers).json()["tickets"], "ADM-1003")

        status_update = client.patch(
            f"/api/tickets/{it_ticket['id']}/status",
            json={"status": "Resolved"},
            headers=headers,
        )
        blocked_update = client.patch(
            f"/api/tickets/{admin_ticket['id']}/status",
            json={"status": "Resolved"},
            headers=headers,
        )

        self.assertEqual(status_update.status_code, 200)
        self.assertEqual(status_update.json()["ticket"]["status"], "Resolved")
        self.assertEqual(blocked_update.status_code, 403)

    def test_finance_manager_can_edit_finance_admin_tickets_but_not_change_status(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")
        tickets = client.get("/api/tickets", headers=headers).json()["tickets"]
        admin_ticket = self.find_ticket(tickets, "ADM-1002")
        admin_ticket_ids = {ticket["ticket_id"] for ticket in tickets}
        self.assertNotIn("IT-1001", admin_ticket_ids)

        edit_payload = {
            "ticket_type": admin_ticket["ticket_type"],
            "title": "Vendor invoice follow-up updated",
            "description": admin_ticket["description"],
            "category": admin_ticket["category"],
            "priority": admin_ticket["priority"],
            "status": admin_ticket["status"],
            "due_date": admin_ticket["due_date"] or None,
            "approval_required": admin_ticket["approval_required"],
        }
        edit_update = client.put(
            f"/api/tickets/{admin_ticket['id']}",
            json=edit_payload,
            headers=headers,
        )
        status_patch = client.patch(
            f"/api/tickets/{admin_ticket['id']}/status",
            json={"status": "In Progress"},
            headers=headers,
        )
        status_put = client.put(
            f"/api/tickets/{admin_ticket['id']}",
            json={**edit_payload, "status": "In Progress"},
            headers=headers,
        )

        self.assertEqual(edit_update.status_code, 200)
        self.assertEqual(edit_update.json()["ticket"]["title"], "Vendor invoice follow-up updated")
        self.assertEqual(edit_update.json()["ticket"]["status"], admin_ticket["status"])
        self.assertEqual(status_patch.status_code, 403)
        self.assertEqual(status_put.status_code, 403)

    def test_finance_manager_can_view_finance_related_admin_tickets(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.get("/api/tickets", headers=headers)

        self.assertEqual(response.status_code, 200)
        tickets = response.json()["tickets"]
        ticket_numbers = {ticket["ticket_id"] for ticket in tickets}
        self.assertIn("ADM-1002", ticket_numbers)
        self.assertNotIn("ADM-1001", ticket_numbers)

    def test_inventory_endpoint_lists_seeded_items_for_admin_and_it_manager(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        admin_response = client.get("/api/inventory", headers=admin_headers)
        it_response = client.get("/api/inventory", headers=it_headers)

        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(it_response.status_code, 200)
        self.assertGreaterEqual(len(admin_response.json()["inventory_items"]), 4)
        self.assertGreaterEqual(len(it_response.json()["inventory_items"]), 4)

    def test_finance_manager_can_view_inventory_but_not_manage_it(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        list_response = client.get("/api/inventory", headers=headers)
        imports_response = client.get("/api/inventory/imports", headers=headers)
        create_response = client.post("/api/inventory", json=self.inventory_payload(), headers=headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(imports_response.status_code, 200)
        self.assertEqual(create_response.status_code, 403)

    def test_employee_cannot_access_inventory(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.get("/api/inventory", headers=headers)

        self.assertEqual(response.status_code, 403)

    def test_create_inventory_item_success_and_audit_log(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post("/api/inventory", json=self.inventory_payload(), headers=headers)

        self.assertEqual(response.status_code, 200)
        item = response.json()["inventory_item"]
        self.assertEqual(item["item_id"], "INV-TEST-1001")
        self.assertEqual(item["category"], "IT Equipment")
        self.assertEqual(item["quantity"], 2)
        self.assertEqual(item["minimum_stock_level"], 1)

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        inventory_log = next(log for log in logs if log["action"] == "inventory.created")
        self.assertEqual(inventory_log["details"]["item_id"], "INV-TEST-1001")
        self.assertEqual(inventory_log["details"]["actor_role"], "admin")

    def test_it_manager_can_update_inventory_item(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=admin_headers)
        item_id = created.json()["inventory_item"]["id"]
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        response = client.put(
            f"/api/inventory/{item_id}",
            json=self.inventory_payload(item_name="Updated Test Laptop", quantity=3, status="Assigned"),
            headers=it_headers,
        )

        self.assertEqual(response.status_code, 200)
        item = response.json()["inventory_item"]
        self.assertEqual(item["item_name"], "Updated Test Laptop")
        self.assertEqual(item["quantity"], 3)
        self.assertEqual(item["status"], "Assigned")

    def test_update_inventory_status_succeeds_and_audits(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=headers)
        item_id = created.json()["inventory_item"]["id"]

        response = client.patch(
            f"/api/inventory/{item_id}/status",
            json={"status": "Submitted to Vendor"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        item = response.json()["inventory_item"]
        self.assertEqual(item["status"], "Submitted to Vendor")
        listed = client.get("/api/inventory", headers=headers).json()["inventory_items"]
        listed_item = next(row for row in listed if row["id"] == item_id)
        self.assertEqual(listed_item["status"], "Submitted to Vendor")
        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        status_log = next(log for log in logs if log["action"] == "inventory.status_updated")
        self.assertEqual(status_log["details"]["item_id"], "INV-TEST-1001")
        self.assertEqual(status_log["details"]["status"], "Submitted to Vendor")
        self.assertEqual(status_log["details"]["actor_role"], "admin")

    def test_update_inventory_status_rejects_invalid_status(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=headers)
        item_id = created.json()["inventory_item"]["id"]

        response = client.patch(
            f"/api/inventory/{item_id}/status",
            json={"status": "Available"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_employee_cannot_update_inventory_status(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=admin_headers)
        item_id = created.json()["inventory_item"]["id"]
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.patch(
            f"/api/inventory/{item_id}/status",
            json={"status": "In Use"},
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_inventory_item_and_audit_log_is_recorded(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        item = created.json()["inventory_item"]

        response = client.delete(f"/api/inventory/{item['id']}", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inventory_item"]["item_id"], "INV-TEST-1001")
        listed = client.get("/api/inventory", headers=headers).json()["inventory_items"]
        self.assertNotIn(item["id"], {inventory_item["id"] for inventory_item in listed})
        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        delete_log = next(log for log in logs if log["action"] == "inventory.item.deleted")
        self.assertEqual(delete_log["details"]["item_id"], "INV-TEST-1001")
        self.assertEqual(delete_log["details"]["actor_role"], "admin")

    def test_it_manager_can_bulk_delete_inventory_items(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        first = client.post("/api/inventory", json=self.inventory_payload(item_id="INV-BULK-1001"), headers=admin_headers)
        second = client.post("/api/inventory", json=self.inventory_payload(item_id="INV-BULK-1002"), headers=admin_headers)
        item_ids = [first.json()["inventory_item"]["id"], second.json()["inventory_item"]["id"]]
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        response = client.post(
            "/api/inventory/bulk-delete",
            json={
                "item_ids": item_ids,
                "selection_mode": "first_50",
                "search": "bulk",
                "filters": {"category": "IT Equipment", "status": "All"},
            },
            headers=it_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_count"], 2)
        listed_ids = {item["id"] for item in client.get("/api/inventory", headers=admin_headers).json()["inventory_items"]}
        self.assertTrue(all(item_id not in listed_ids for item_id in item_ids))
        logs = client.get("/api/audit-log", headers=admin_headers).json()["audit_logs"]
        bulk_log = next(log for log in logs if log["action"] == "inventory.items.bulk_deleted")
        self.assertEqual(bulk_log["details"]["deleted_count"], 2)
        self.assertEqual(bulk_log["details"]["selection_mode"], "first_50")
        self.assertEqual(bulk_log["details"]["search"], "bulk")
        self.assertEqual(bulk_log["details"]["filters"]["category"], "IT Equipment")
        self.assertEqual(bulk_log["details"]["actor_role"], "it_manager")

    def test_employee_cannot_delete_inventory_item(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(), headers=admin_headers)
        item_id = created.json()["inventory_item"]["id"]
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        delete_response = client.delete(f"/api/inventory/{item_id}", headers=employee_headers)
        bulk_response = client.post("/api/inventory/bulk-delete", json={"item_ids": [item_id]}, headers=employee_headers)

        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(bulk_response.status_code, 403)

    def test_inventory_create_rejects_unknown_category_and_missing_required_fields(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        bad_category = client.post(
            "/api/inventory",
            json=self.inventory_payload(category="Furniture"),
            headers=headers,
        )
        missing_name_payload = self.inventory_payload()
        missing_name_payload.pop("item_name")
        missing_name = client.post("/api/inventory", json=missing_name_payload, headers=headers)

        self.assertEqual(bad_category.status_code, 422)
        self.assertEqual(missing_name.status_code, 422)

    def test_inventory_import_preview_accepts_csv_and_reports_row_warnings(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = (
            "Item ID,Item Name,Category,Quantity,Unit,Condition,Location,Department,Minimum Stock Level,Status\n"
            "INV-CSV-1001,Desk Lamp,Unknown Category,5,pcs,Good,Admin Store,Admin,2,Available\n"
        ).encode("utf-8")

        response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory.csv", csv_content),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview["file_type"], "csv")
        self.assertEqual(len(preview["rows"]), 1)
        self.assertEqual(preview["rows"][0]["item"]["item_id"], "INV-CSV-1001")
        self.assertEqual(preview["rows"][0]["item"]["category"], "Other")
        self.assertTrue(preview["warnings"])
        self.assertFalse(preview["errors"])

    def test_inventory_import_preview_accepts_xlsx(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        rows = [
            ["Item ID", "Item Name", "Category", "Quantity", "Unit", "Condition", "Location", "Department", "Minimum Stock Level", "Status"],
            ["INV-XLSX-1001", "Onboarding Backpack", "Onboarding Equipment", "7", "pcs", "New", "HR Cabinet", "HR", "3", "Available"],
        ]

        response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory.xlsx", self.make_xlsx(rows)),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview["file_type"], "xlsx")
        self.assertEqual(preview["rows"][0]["item"]["item_id"], "INV-XLSX-1001")
        self.assertEqual(preview["rows"][0]["item"]["category"], "Onboarding Equipment")
        self.assertFalse(preview["errors"])

    def test_inventory_import_preview_accepts_missing_optional_new_columns(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = (
            "Employee,Serial Number,Model Number,RAM,Office Location\n"
            "Asha Mehta,DL-5440-099,Latitude 5440,16 GB,Pune\n"
        ).encode("utf-8")

        response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory-flexible.csv", csv_content),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertFalse(preview["errors"])
        self.assertEqual(preview["detected_columns"], ["Employee name", "Serial No.", "Model No.", "RAM", "Location"])
        self.assertEqual(preview["header_row_number"], 1)
        self.assertIn("Missing optional columns defaulted: Disk, Status, Notes", preview["warnings"])
        item = preview["rows"][0]["item"]
        self.assertEqual(item["employee_name"], "Asha Mehta")
        self.assertEqual(item["serial_no"], "DL-5440-099")
        self.assertEqual(item["model_no"], "Latitude 5440")
        self.assertEqual(item["ram"], "16 GB")
        self.assertEqual(item["disk"], "")
        self.assertEqual(item["location"], "Pune")
        self.assertEqual(item["status"], "In Use")
        self.assertEqual(item["notes"], "")

    def test_inventory_import_preview_detects_headers_after_title_rows(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        rows = [
            ["GP Employee data 1"],
            ["Generated report", "", "", ""],
            ["Name", "Service Tag", "Model", "Memory", "Comments"],
            ["Geeta Pawar", "ST-GP-778", "Latitude 7440", "16 GB", "Assigned replacement laptop"],
        ]

        response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("GP Employee data 1.xlsx", self.make_xlsx(rows)),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertFalse(preview["errors"])
        self.assertEqual(preview["header_row_number"], 3)
        self.assertEqual(preview["detected_columns"], ["Employee name", "Serial No.", "Model No.", "RAM", "Notes"])
        self.assertIn("Missing optional columns defaulted: Disk, Location, Status", preview["warnings"])
        item = preview["rows"][0]["item"]
        self.assertEqual(item["employee_name"], "Geeta Pawar")
        self.assertEqual(item["serial_no"], "ST-GP-778")
        self.assertEqual(item["model_no"], "Latitude 7440")
        self.assertEqual(item["ram"], "16 GB")
        self.assertEqual(item["status"], "In Use")
        self.assertEqual(item["notes"], "Assigned replacement laptop")

    def test_inventory_import_accepts_gp_employee_excel_headers_and_all_rows(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        rows = [
            ["GP Employee data 1"],
            ["Num", "Name's", "Sr. No.", '"Laptop" Brand', "RAM", "Location"],
        ]
        for index in range(1, 62):
            rows.append([str(index), f"Employee {index}", f"SR-{index:03d}", f"Dell Latitude {index}", "16 GB", "Pune"])

        preview_response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("GP Employee data 1.xlsx", self.make_xlsx(rows)),
            headers=headers,
        )

        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.json()
        self.assertFalse(preview["errors"])
        self.assertEqual(preview["header_row_number"], 2)
        self.assertEqual(preview["detected_columns"], ["Employee name", "Serial No.", "Model No.", "RAM", "Location"])
        self.assertEqual(len(preview["rows"]), 61)
        self.assertIn("Missing optional columns defaulted: Disk, Status, Notes", preview["warnings"])
        first_item = preview["rows"][0]["item"]
        self.assertEqual(first_item["employee_name"], "Employee 1")
        self.assertEqual(first_item["serial_no"], "SR-001")
        self.assertEqual(first_item["model_no"], "Dell Latitude 1")
        self.assertEqual(first_item["ram"], "16 GB")
        self.assertEqual(first_item["disk"], "")
        self.assertEqual(first_item["location"], "Pune")
        self.assertEqual(first_item["status"], "In Use")
        self.assertEqual(first_item["notes"], "")

        import_response = client.post(
            "/api/inventory/imports",
            json={"filename": "GP Employee data 1.xlsx", "items": [row["item"] for row in preview["rows"]]},
            headers=headers,
        )

        self.assertEqual(import_response.status_code, 200)
        payload = import_response.json()
        self.assertEqual(payload["import"]["successful_rows"], 61)
        self.assertEqual(payload["import"]["failed_rows"], 0)
        self.assertEqual(payload["import"]["status"], "Completed")

    def test_inventory_import_confirm_saves_defaults_for_missing_optional_new_columns(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = (
            "Assigned To,Asset Serial,Model,Memory\n"
            "Ravi Patil,HP-840-778,EliteBook 840,8 GB\n"
        ).encode("utf-8")
        preview = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory-flexible.csv", csv_content),
            headers=headers,
        ).json()

        response = client.post(
            "/api/inventory/imports",
            json={"filename": "inventory-flexible.csv", "items": [preview["rows"][0]["item"]]},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["import"]["successful_rows"], 1)
        imported_item = payload["inventory_items"][0]
        self.assertEqual(imported_item["employee_name"], "Ravi Patil")
        self.assertEqual(imported_item["serial_no"], "HP-840-778")
        self.assertEqual(imported_item["model_no"], "EliteBook 840")
        self.assertEqual(imported_item["ram"], "8 GB")
        self.assertEqual(imported_item["disk"], "")
        self.assertEqual(imported_item["location"], "")
        self.assertEqual(imported_item["status"], "In Use")
        self.assertEqual(imported_item["notes"], "")

    def test_inventory_import_preview_missing_required_columns_shows_template_message(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = "Unrelated,Another\nDesk Lamp,5\n".encode("utf-8")

        response = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("wrong-format.csv", csv_content),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(
            preview["errors"],
            ["This file does not match the inventory template. Please download and use the sample template."],
        )

    def test_inventory_import_preview_rejects_unsupported_files_and_empty_files(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        legacy_excel = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory.xls", b"legacy"),
            headers=headers,
        )
        empty_file = client.post(
            "/api/inventory/import/preview",
            json=self.inventory_import_payload("inventory.csv", b""),
            headers=headers,
        )

        self.assertEqual(legacy_excel.status_code, 400)
        self.assertIn(".xls import is not enabled", legacy_excel.json()["detail"])
        self.assertEqual(empty_file.status_code, 422)

    def test_inventory_import_create_tracks_batch_and_links_items(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        items = [
            self.inventory_payload(item_id="INV-IMPORT-1001"),
            self.inventory_payload(item_id="INV-IMPORT-1002", item_name="Imported Monitor"),
        ]

        response = client.post(
            "/api/inventory/imports",
            json={"filename": "corrected_inventory.xlsx", "items": items},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        batch = payload["import"]
        self.assertEqual(batch["file_name"], "corrected_inventory.xlsx")
        self.assertEqual(batch["successful_rows"], 2)
        self.assertEqual(batch["failed_rows"], 0)
        self.assertEqual(batch["status"], "Completed")
        self.assertTrue(all(item["import_batch_id"] == batch["id"] for item in payload["inventory_items"]))

        imports = client.get("/api/inventory/imports", headers=headers).json()["imports"]
        self.assertTrue(any(import_batch["id"] == batch["id"] for import_batch in imports))
        import_items = client.get(f"/api/inventory/imports/{batch['id']}/items", headers=headers)
        self.assertEqual(import_items.status_code, 200)
        self.assertEqual(len(import_items.json()["inventory_items"]), 2)

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        import_log = next(log for log in logs if log["action"] == "inventory.import.created")
        self.assertEqual(import_log["details"]["file_name"], "corrected_inventory.xlsx")
        self.assertEqual(import_log["details"]["successful_rows"], 2)

    def test_delete_inventory_import_batch_deletes_only_imported_items(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        manual = client.post("/api/inventory", json=self.inventory_payload(item_id="INV-MANUAL-1001"), headers=headers)
        items = [
            self.inventory_payload(item_id="INV-BATCH-1001"),
            self.inventory_payload(item_id="INV-BATCH-1002"),
        ]
        created_import = client.post(
            "/api/inventory/imports",
            json={"filename": "bad_import.csv", "items": items},
            headers=headers,
        ).json()["import"]

        response = client.delete(f"/api/inventory/imports/{created_import['id']}", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_count"], 2)
        listed = client.get("/api/inventory", headers=headers).json()["inventory_items"]
        listed_item_ids = {item["item_id"] for item in listed}
        self.assertIn(manual.json()["inventory_item"]["item_id"], listed_item_ids)
        self.assertNotIn("INV-BATCH-1001", listed_item_ids)
        imports = client.get("/api/inventory/imports", headers=headers).json()["imports"]
        deleted_batch = next(import_batch for import_batch in imports if import_batch["id"] == created_import["id"])
        self.assertEqual(deleted_batch["status"], "Deleted")
        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        delete_log = next(log for log in logs if log["action"] == "inventory.import.deleted")
        self.assertEqual(delete_log["details"]["file_name"], "bad_import.csv")

    def test_employee_cannot_delete_inventory_import_batch(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created_import = client.post(
            "/api/inventory/imports",
            json={"filename": "restricted.csv", "items": [self.inventory_payload(item_id="INV-REST-1001")]},
            headers=admin_headers,
        ).json()["import"]
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.delete(f"/api/inventory/imports/{created_import['id']}", headers=employee_headers)

        self.assertEqual(response.status_code, 403)

    def test_legacy_unbatched_inventory_cleanup_is_admin_only(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/inventory", json=self.inventory_payload(item_id="INV-LEGACY-1001"), headers=admin_headers)
        self.assertIsNone(created.json()["inventory_item"]["import_batch_id"])
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        blocked = client.delete("/api/inventory/imports/legacy-unbatched", headers=it_headers)
        deleted = client.delete("/api/inventory/imports/legacy-unbatched", headers=admin_headers)

        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(deleted.status_code, 200)
        self.assertGreaterEqual(deleted.json()["deleted_count"], 1)

    def vendor_payload(self, **overrides):
        payload = {
            "vendor_name": "North Star Transport",
            "contact_person": "Maya Rao",
            "email": "maya.rao@northstar.example",
            "contact_details": "+91 98765 43210",
            "office_address": "42 MG Road, Bengaluru, Karnataka",
            "service_provided": "Transport",
            "start_date": "2026-05-10",
            "end_date": "2027-05-09",
            "billing_amount": 12000,
            "billing_cycle": "Monthly",
        }
        payload.update(overrides)
        return payload

    def test_create_vendor_success(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["vendor_name"], "North Star Transport")
        self.assertEqual(vendor["contact_person"], "Maya Rao")
        self.assertEqual(vendor["email"], "maya.rao@northstar.example")
        self.assertEqual(vendor["service_provided"], "Transport")
        self.assertEqual(vendor["start_date"], "2026-05-10")
        self.assertEqual(vendor["end_date"], "2027-05-09")
        self.assertEqual(vendor["billing_amount"], 12000)
        self.assertEqual(vendor["billing_cycle"], "Monthly")
        self.assertEqual(vendor["status"], "active")

    def test_create_vendor_missing_required_field_fails(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        payload = self.vendor_payload()
        payload.pop("vendor_name")

        response = client.post("/api/vendors", json=payload, headers=headers)

        self.assertEqual(response.status_code, 422)

    def test_create_vendor_billing_amount_required(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        payload = self.vendor_payload()
        payload.pop("billing_amount")

        response = client.post("/api/vendors", json=payload, headers=headers)

        self.assertEqual(response.status_code, 422)

    def test_create_vendor_billing_amount_must_be_numeric_and_positive(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        non_numeric = client.post(
            "/api/vendors",
            json=self.vendor_payload(billing_amount="abc"),
            headers=headers,
        )
        zero = client.post(
            "/api/vendors",
            json=self.vendor_payload(billing_amount=0),
            headers=headers,
        )

        self.assertEqual(non_numeric.status_code, 422)
        self.assertEqual(zero.status_code, 422)

    def test_create_vendor_start_date_required(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        payload = self.vendor_payload()
        payload.pop("start_date")

        response = client.post("/api/vendors", json=payload, headers=headers)

        self.assertEqual(response.status_code, 422)

    def test_create_vendor_end_date_is_optional(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        payload = self.vendor_payload()
        payload.pop("end_date")

        response = client.post("/api/vendors", json=payload, headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vendor"]["end_date"], "")

    def test_create_vendor_empty_string_end_date_is_optional(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/vendors",
            json=self.vendor_payload(end_date=""),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vendor"]["end_date"], "")

    def test_create_vendor_invalid_date_fails(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/vendors",
            json=self.vendor_payload(start_date="32/15/2026"),
            headers=headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_list_vendors_includes_created_vendor(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        create = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(create.status_code, 200)
        response = client.get("/api/vendors", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendors = response.json()["vendors"]
        self.assertEqual(len(vendors), 1)
        self.assertIsInstance(vendors[0]["id"], int)
        self.assertEqual(vendors[0]["vendor_name"], "North Star Transport")
        self.assertEqual(vendors[0]["office_address"], "42 MG Road, Bengaluru, Karnataka")
        self.assertEqual(vendors[0]["billing_amount"], 12000)

    def test_existing_vendor_table_without_billing_amount_is_migrated(self):
        db_path = Path(self.tmp.name) / "legacy_vendor.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT NOT NULL,
                    contact_person TEXT NOT NULL,
                    email TEXT NOT NULL,
                    contact_details TEXT NOT NULL,
                    office_address TEXT NOT NULL,
                    service_provided TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    billing_cycle TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO vendors (
                    vendor_name, contact_person, email, contact_details,
                    office_address, service_provided, start_date, end_date,
                    billing_cycle, status, created_by_user_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Legacy Vendor",
                    "Maya Rao",
                    "maya.rao@legacy.example",
                    "+91 98765 43210",
                    "42 MG Road, Bengaluru",
                    "Transport",
                    "2026-05-10",
                    "",
                    "Monthly",
                    "active",
                    None,
                    "2026-05-01T00:00:00+00:00",
                    "2026-05-01T00:00:00+00:00",
                ),
            )

        repo = AdminRepository(db_path)
        vendors = repo.list_vendors()

        self.assertEqual(vendors[0]["billing_amount"], 0)

        updated = repo.update_vendor(
            vendors[0]["id"],
            {"billing_amount": 2500, "billing_cycle": "Yearly"},
        )
        self.assertEqual(updated["billing_amount"], 2500)
        self.assertEqual(updated["billing_cycle"], "Yearly")
        self.assertEqual(repo.list_vendors()[0]["billing_amount"], 2500)

    def test_legacy_vendor_table_api_update_saves_billing_amount(self):
        from fastapi.testclient import TestClient

        db_path = Path(self.tmp.name) / "legacy_vendor_api.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT NOT NULL,
                    contact_person TEXT NOT NULL,
                    email TEXT NOT NULL,
                    contact_details TEXT NOT NULL,
                    office_address TEXT NOT NULL,
                    service_provided TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    billing_cycle TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO vendors (
                    vendor_name, contact_person, email, contact_details,
                    office_address, service_provided, start_date, end_date,
                    billing_cycle, status, created_by_user_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Legacy API Vendor",
                    "Maya Rao",
                    "maya.rao@legacy-api.example",
                    "+91 98765 43210",
                    "42 MG Road, Bengaluru",
                    "Transport",
                    "2026-05-10",
                    "",
                    "Quarterly",
                    "active",
                    None,
                    "2026-05-01T00:00:00+00:00",
                    "2026-05-01T00:00:00+00:00",
                ),
            )

        app = create_app(database_path=db_path)
        client = TestClient(app)
        headers = self.auth_headers(client)

        before = client.get("/api/vendors", headers=headers)
        self.assertEqual(before.status_code, 200)
        vendor_id = before.json()["vendors"][0]["id"]
        self.assertEqual(before.json()["vendors"][0]["billing_amount"], 0)

        update = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(
                vendor_name="Legacy API Vendor",
                email="maya.rao@legacy-api.example",
                end_date="",
                billing_amount=43231,
                billing_cycle="Monthly",
            ),
            headers=headers,
        )

        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["vendor"]["billing_amount"], 43231)
        self.assertEqual(update.json()["vendor"]["billing_cycle"], "Monthly")

        after = client.get("/api/vendors", headers=headers)
        updated_vendor = next(item for item in after.json()["vendors"] if item["id"] == vendor_id)
        self.assertEqual(updated_vendor["billing_amount"], 43231)
        self.assertEqual(updated_vendor["billing_cycle"], "Monthly")

    def test_get_vendors_returns_id_for_every_vendor(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        for index in range(2):
            create = client.post(
                "/api/vendors",
                json=self.vendor_payload(vendor_name=f"Vendor {index}"),
                headers=headers,
            )
            self.assertEqual(create.status_code, 200)

        response = client.get("/api/vendors", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendors = response.json()["vendors"]
        self.assertGreaterEqual(len(vendors), 2)
        self.assertTrue(all(isinstance(vendor.get("id"), int) for vendor in vendors))

    def test_update_vendor_works(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        vendor_id = created.json()["vendor"]["id"]

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(
                vendor_name="North Star Mobility",
                office_address="99 Residency Road, Bengaluru",
                start_date="2026-01-15",
                end_date="2026-05-15",
                billing_amount=18000,
                billing_cycle="Quarterly",
            ),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["id"], vendor_id)
        self.assertEqual(vendor["vendor_name"], "North Star Mobility")
        self.assertEqual(vendor["office_address"], "99 Residency Road, Bengaluru")
        self.assertEqual(vendor["start_date"], "2026-01-15")
        self.assertEqual(vendor["end_date"], "2026-05-15")
        self.assertEqual(vendor["billing_amount"], 18000)
        self.assertEqual(vendor["billing_cycle"], "Quarterly")

        listed = client.get("/api/vendors", headers=headers)
        listed_vendor = next(item for item in listed.json()["vendors"] if item["id"] == vendor_id)
        self.assertEqual(listed_vendor["billing_amount"], 18000)
        self.assertEqual(listed_vendor["billing_cycle"], "Quarterly")

    def test_update_vendor_saves_billing_amount_from_zero_to_quarterly(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post(
            "/api/vendors",
            json=self.vendor_payload(billing_amount=1000, billing_cycle="Monthly"),
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        vendor_id = created.json()["vendor"]["id"]
        app_repo_vendor = created.json()["vendor"]
        self.assertEqual(app_repo_vendor["billing_amount"], 1000)

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(billing_amount=5232, billing_cycle="Quarterly"),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vendor"]["billing_amount"], 5232)
        self.assertEqual(response.json()["vendor"]["billing_cycle"], "Quarterly")

        listed = client.get("/api/vendors", headers=headers)
        listed_vendor = next(item for item in listed.json()["vendors"] if item["id"] == vendor_id)
        self.assertEqual(listed_vendor["billing_amount"], 5232)
        self.assertEqual(listed_vendor["billing_cycle"], "Quarterly")

    def test_update_vendor_saves_billing_amount_to_monthly(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        vendor_id = created.json()["vendor"]["id"]

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(billing_amount=43231, billing_cycle="Monthly"),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vendor"]["billing_amount"], 43231)
        self.assertEqual(response.json()["vendor"]["billing_cycle"], "Monthly")

        listed = client.get("/api/vendors", headers=headers)
        listed_vendor = next(item for item in listed.json()["vendors"] if item["id"] == vendor_id)
        self.assertEqual(listed_vendor["billing_amount"], 43231)
        self.assertEqual(listed_vendor["billing_cycle"], "Monthly")

    def test_update_vendor_can_clear_end_date(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        vendor_id = created.json()["vendor"]["id"]

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(end_date=""),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["vendor"]["end_date"], "")

    def test_unauthorized_role_cannot_create_vendor(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)

        self.assertEqual(response.status_code, 403)
        self.assertIn("Admin role required", response.json()["detail"])

    def test_finance_manager_can_view_vendors_but_employee_cannot(self):
        client, _ = self.api_client()
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        finance_response = client.get("/api/vendors", headers=finance_headers)
        employee_response = client.get("/api/vendors", headers=employee_headers)

        self.assertEqual(finance_response.status_code, 200)
        self.assertEqual(employee_response.status_code, 403)

    def test_unauthorized_role_cannot_update_vendor(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=admin_headers)
        vendor_id = created.json()["vendor"]["id"]
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(vendor_name="Blocked Update"),
            headers=finance_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_vendor_creation_records_audit_log(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        created_log = next(log for log in logs if log["action"] == "vendor.created")
        self.assertEqual(created_log["actor"], "admin@company.com")
        self.assertEqual(created_log["details"]["vendor_name"], vendor["vendor_name"])
        self.assertEqual(created_log["details"]["actor_role"], "admin")

    def test_vendor_update_records_audit_log(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        vendor_id = created.json()["vendor"]["id"]

        response = client.put(
            f"/api/vendors/{vendor_id}",
            json=self.vendor_payload(vendor_name="Updated North Star"),
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        updated_log = next(log for log in logs if log["action"] == "vendor.updated")
        self.assertEqual(updated_log["actor"], "admin@company.com")
        self.assertEqual(updated_log["details"]["vendor_name"], "Updated North Star")
        self.assertEqual(updated_log["details"]["actor_role"], "admin")

    def test_close_active_vendor_sets_status_closed(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        vendor_id = created.json()["vendor"]["id"]

        response = client.patch(f"/api/vendors/{vendor_id}/close", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["status"], "closed")

    def test_close_missing_vendor_returns_404(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.patch("/api/vendors/99999/close", headers=headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Vendor not found")

    def test_reopen_missing_vendor_returns_404(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.patch("/api/vendors/99999/reopen", headers=headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Vendor not found")

    def test_close_active_vendor_without_end_date_sets_today(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post(
            "/api/vendors",
            json=self.vendor_payload(end_date=""),
            headers=headers,
        )
        vendor_id = created.json()["vendor"]["id"]
        today = datetime.now(timezone.utc).date().isoformat()

        response = client.patch(f"/api/vendors/{vendor_id}/close", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["status"], "closed")
        self.assertEqual(vendor["end_date"], today)

    def test_close_active_vendor_with_existing_end_date_keeps_it(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post(
            "/api/vendors",
            json=self.vendor_payload(end_date="2027-04-30"),
            headers=headers,
        )
        vendor_id = created.json()["vendor"]["id"]

        response = client.patch(f"/api/vendors/{vendor_id}/close", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["status"], "closed")
        self.assertEqual(vendor["end_date"], "2027-04-30")

    def test_reopen_closed_vendor_changes_status_active(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        vendor_id = created.json()["vendor"]["id"]
        close = client.patch(f"/api/vendors/{vendor_id}/close", headers=headers)
        self.assertEqual(close.status_code, 200)

        response = client.patch(f"/api/vendors/{vendor_id}/reopen", headers=headers)

        self.assertEqual(response.status_code, 200)
        vendor = response.json()["vendor"]
        self.assertEqual(vendor["status"], "active")
        self.assertEqual(vendor["end_date"], "2027-05-09")

    def test_unauthorized_role_cannot_close_or_reopen_vendor(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=admin_headers)
        vendor_id = created.json()["vendor"]["id"]
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        close = client.patch(f"/api/vendors/{vendor_id}/close", headers=finance_headers)
        reopen = client.patch(f"/api/vendors/{vendor_id}/reopen", headers=finance_headers)

        self.assertEqual(close.status_code, 403)
        self.assertEqual(reopen.status_code, 403)

    def test_vendor_close_and_reopen_records_audit_logs(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        vendor_id = created.json()["vendor"]["id"]

        close = client.patch(f"/api/vendors/{vendor_id}/close", headers=headers)
        reopen = client.patch(f"/api/vendors/{vendor_id}/reopen", headers=headers)

        self.assertEqual(close.status_code, 200)
        self.assertEqual(reopen.status_code, 200)
        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        closed_log = next(log for log in logs if log["action"] == "vendor.closed")
        reopened_log = next(log for log in logs if log["action"] == "vendor.reopened")
        self.assertEqual(closed_log["actor"], "admin@company.com")
        self.assertEqual(closed_log["details"]["vendor_id"], vendor_id)
        self.assertEqual(reopened_log["actor"], "admin@company.com")
        self.assertEqual(reopened_log["details"]["vendor_id"], vendor_id)

    def test_vendor_email_action_queues_approval_and_audit_log(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=headers)
        vendor = created.json()["vendor"]

        response = client.post(
            f"/api/vendors/{vendor['id']}/email",
            json={
                "subject": "Quarterly review follow-up",
                "body": "Please review the attached action items for the next vendor review.",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pending_approval")
        self.assertEqual(payload["message"], "Vendor email sent to approval queue")
        self.assertEqual(payload["approval"]["approval_type"], "external_vendor_email")
        self.assertEqual(payload["approval"]["status"], "pending")
        self.assertEqual(payload["approval"]["recipient_email"], vendor["email"])
        self.assertEqual(payload["approval"]["required_roles"], ["admin"])
        self.assertEqual(payload["route"]["required_approval_roles"], ["admin"])

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        drafted_log = next(log for log in logs if log["action"] == "vendor.email.drafted")
        self.assertEqual(drafted_log["actor"], "admin@company.com")
        self.assertEqual(drafted_log["status"], "pending_approval")
        self.assertTrue(drafted_log["approval_required"])
        self.assertEqual(drafted_log["details"]["vendor_id"], vendor["id"])
        self.assertEqual(drafted_log["details"]["recipient_email"], vendor["email"])
        self.assertIn("approval.queued", {log["action"] for log in logs})

    def test_unauthorized_role_cannot_send_vendor_email(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        created = client.post("/api/vendors", json=self.vendor_payload(), headers=admin_headers)
        vendor_id = created.json()["vendor"]["id"]
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.post(
            f"/api/vendors/{vendor_id}/email",
            json={"subject": "Vendor follow-up", "body": "Please review this update."},
            headers=finance_headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Admin role required", response.json()["detail"])

    def test_create_vendor_alphabet_date_fails(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/vendors",
            json=self.vendor_payload(start_date="dads", end_date="dsaa"),
            headers=headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_create_vendor_end_date_before_start_date_fails(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/vendors",
            json=self.vendor_payload(start_date="2026-05-15", end_date="2026-01-15"),
            headers=headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_agent_plan_vendor_followup_requires_approval(self):
        planner = MockAdminAgentPlanner()

        plan = planner.create_plan("Draft a vendor follow-up email after the review meeting.")

        self.assertEqual(plan["task_type"], "vendor_management")
        self.assertEqual(plan["automation_level"], "needs_human_approval")
        self.assertTrue(plan["approval_required"])
        self.assertIn("External vendor communication", plan["approval_reason"])
        self.assertIn("mock_approval_queue", plan["required_tools"])

    def test_agent_plan_reminders_are_automatic(self):
        planner = MockAdminAgentPlanner()

        plan = planner.create_plan("Remind everyone about tomorrow's internal staff meeting.")

        self.assertEqual(plan["task_type"], "reminder_management")
        self.assertEqual(plan["automation_level"], "automatic")
        self.assertFalse(plan["approval_required"])
        self.assertEqual(plan["approval_reason"], "")

    def test_agent_plan_expense_approval_requires_human_approval(self):
        planner = MockAdminAgentPlanner()

        plan = planner.create_plan("Approve Priya's expense report for reimbursement.")

        self.assertEqual(plan["task_type"], "expense_management")
        self.assertEqual(plan["automation_level"], "needs_human_approval")
        self.assertTrue(plan["approval_required"])
        self.assertIn("Expense approvals", plan["approval_reason"])

    def test_agent_plan_file_deletion_requires_human_approval(self):
        planner = MockAdminAgentPlanner()

        plan = planner.create_plan("Delete files from the confidential contract folder.")

        self.assertEqual(plan["task_type"], "document_management")
        self.assertEqual(plan["automation_level"], "needs_human_approval")
        self.assertTrue(plan["approval_required"])
        self.assertIn("File deletion", plan["approval_reason"])

    def test_agent_plan_unknown_high_risk_request_requires_human_decision(self):
        planner = MockAdminAgentPlanner()

        plan = planner.create_plan(
            "Make an undefined emergency safety policy exception without asking anyone."
        )

        self.assertEqual(plan["automation_level"], "human_decision_required")
        self.assertTrue(plan["approval_required"])
        self.assertEqual(plan["risk_level"], "critical")
        self.assertIn("Emergency or safety decisions", plan["approval_reason"])

    def test_agent_planner_falls_back_to_mock_without_openai_api_key(self):
        class Settings:
            openai_api_key = ""
            openai_model = "gpt-5.5"

        planner = get_agent_planner(Settings)
        plan = planner.create_plan("Remind Maya about tomorrow's meeting.")

        self.assertIsInstance(planner, MockAdminAgentPlanner)
        self.assertEqual(planner.mode, "mock_agent_planner")
        self.assertEqual(plan["task_type"], "reminder_management")
        self.assertEqual(plan["automation_level"], "automatic")

    def test_placeholder_openai_api_key_is_treated_as_missing(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "replace_with_your_openai_api_key"}):
            self.assertEqual(openai_api_key_from_env(), "")

    def test_missing_openai_api_key_uses_mock_mode(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(openai_api_key_from_env(), "")

        class Settings:
            openai_api_key = ""
            openai_model = "gpt-5.5"

        planner = get_agent_planner(Settings)
        self.assertIsInstance(planner, MockAdminAgentPlanner)
        self.assertEqual(planner.mode, "mock_agent_planner")

    def test_real_looking_openai_api_key_selects_openai_planner_without_exposing_key(self):
        fake_api_key = "sk-" + ("x" * 40)

        class Settings:
            openai_api_key = fake_api_key
            openai_model = "gpt-5.5"

        planner = get_agent_planner(Settings)

        self.assertIsInstance(planner, OpenAIResponsesAdminAgentPlanner)
        self.assertEqual(planner.mode, "openai_responses_agent_planner")

    def test_env_example_does_not_contain_real_openai_api_key(self):
        env_example = ROOT.parent / ".env.example"
        content = env_example.read_text()

        self.assertIn("OPENAI_API_KEY=", content)
        self.assertIn("AI_PROVIDER=deepinfra", content)
        self.assertIn("DEEPINFRA_API_KEY=", content)
        self.assertIn("DEEPINFRA_MODEL=deepseek-ai/DeepSeek-V3", content)
        self.assertNotIn("replace_with_your_openai_api_key", content)
        for line in content.splitlines():
            if line.startswith("OPENAI_API_KEY="):
                self.assertEqual(line, "OPENAI_API_KEY=")
            if line.startswith("DEEPINFRA_API_KEY="):
                self.assertEqual(line, "DEEPINFRA_API_KEY=")

    def test_placeholder_deepinfra_api_key_is_treated_as_missing(self):
        with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "PASTE_YOUR_DEEPINFRA_API_KEY_HERE"}):
            self.assertEqual(deepinfra_api_key_from_env(), "")

    def test_deepinfra_client_requires_provider_and_key(self):
        class MissingKeySettings:
            ai_provider = "deepinfra"
            deepinfra_api_key = ""
            deepinfra_model = "deepseek-ai/DeepSeek-V3"

        class MockProviderSettings:
            ai_provider = "mock"
            deepinfra_api_key = "df-" + ("x" * 32)
            deepinfra_model = "deepseek-ai/DeepSeek-V3"

        class DisabledProviderSettings:
            ai_provider = "disabled"
            deepinfra_api_key = "df-" + ("x" * 32)
            deepinfra_model = "deepseek-ai/DeepSeek-V3"

        class DeepInfraSettings:
            ai_provider = "deepinfra"
            deepinfra_api_key = "df-" + ("x" * 32)
            deepinfra_model = "deepseek-ai/DeepSeek-V3"

        self.assertIsNone(get_deepinfra_client(MissingKeySettings))
        self.assertIsNone(get_deepinfra_client(DisabledProviderSettings))
        self.assertIsNone(get_deepinfra_client(MockProviderSettings))
        client = get_deepinfra_client(DeepInfraSettings)
        self.assertIsInstance(client, DeepInfraChatClient)
        self.assertEqual(client.model, "deepseek-ai/DeepSeek-V3")

    def test_deepinfra_client_uses_openai_compatible_chat_endpoint(self):
        captured = {}

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({
                                    "intent": "open_tickets",
                                    "confidence": 0.91,
                                    "entities": {},
                                    "required_role_scope": "tickets",
                                    "action_type": "fetch",
                                    "missing_fields": [],
                                    "confirmation_required": False,
                                })
                            }
                        }
                    ]
                }).encode("utf-8")

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return DummyResponse()

        client = DeepInfraChatClient(api_key="df-test-key", model="deepseek-ai/DeepSeek-V3")
        with patch("urllib.request.urlopen", fake_urlopen):
            result = client.classify_intent("show open tickets", ["open_tickets", "unsupported"])

        self.assertEqual(captured["url"], "https://api.deepinfra.com/v1/openai/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer df-test-key")
        self.assertEqual(captured["payload"]["model"], "deepseek-ai/DeepSeek-V3")
        self.assertEqual(result["intent"], "open_tickets")
        self.assertGreater(result["confidence"], 0.9)

    def test_deepinfra_json_parser_accepts_wrapped_json(self):
        parsed = parse_json_object("Here is JSON:\n{\"answer\": \"ok\", \"bullets\": []}")
        self.assertEqual(parsed["answer"], "ok")

    def test_agent_plan_endpoint_returns_structured_plan(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        response = client.post(
            "/api/agent/plan",
            json={"message": "Remind everyone about tomorrow's internal staff meeting."},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["planner_mode"], "mock_agent_planner")
        self.assertEqual(payload["agent_plan"]["task_type"], "reminder_management")
        self.assertEqual(payload["agent_plan"]["automation_level"], "automatic")
        self.assertIn("required_tools", payload["agent_plan"])

    def test_valid_login_works(self):
        client, _ = self.api_client()

        response = client.post(
            "/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["token"])
        self.assertEqual(payload["user"]["email"], "admin@company.com")
        self.assertEqual(payload["user"]["role"], "admin")
        self.assertNotIn("password", payload["user"])

    def test_all_demo_users_can_login(self):
        client, _ = self.api_client()
        demo_users = [
            ("admin@company.com", "admin123", "admin"),
            ("finance@company.com", "finance123", "finance_manager"),
            ("it@company.com", "it123", "it_manager"),
            ("employee@company.com", "employee123", "employee"),
        ]

        for email, password, role in demo_users:
            response = client.post(
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["user"]["role"], role)

        legacy_operation = client.post(
            "/api/auth/login",
            json={"email": "operation@company.com", "password": "operation123"},
        )
        self.assertEqual(legacy_operation.status_code, 401)

    def test_demo_user_seed_repairs_disabled_demo_accounts(self):
        repo = self.repo
        repo.seed_demo_users()
        admin = repo.get_user_by_email("admin@company.com")
        repo.update_user(admin["id"], enabled=False, password="changed", role="employee")

        repo.seed_demo_users()
        repaired = repo.get_user_by_email("admin@company.com")

        self.assertTrue(repaired["enabled"])
        self.assertEqual(repaired["password"], "admin123")
        self.assertEqual(repaired["role"], "admin")

    def test_invalid_login_fails(self):
        client, _ = self.api_client()

        response = client.post(
            "/api/auth/login",
            json={"email": "admin@company.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)

    def test_logout_invalidates_session(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        logout = client.post("/api/auth/logout", headers=headers)
        me = client.get("/api/auth/me", headers=headers)

        self.assertEqual(logout.status_code, 200)
        self.assertEqual(me.status_code, 401)

    def test_protected_pages_require_login(self):
        client, _ = self.api_client()

        for method, path in [
            ("GET", "/api/dashboard"),
            ("GET", "/api/approvals"),
            ("GET", "/api/audit-log"),
            ("GET", "/api/tickets"),
            ("GET", "/api/notifications"),
            ("GET", "/api/vendors"),
            ("GET", "/api/expenses"),
            ("GET", "/api/inventory"),
            ("GET", "/api/users"),
            ("POST", "/api/chat/command"),
        ]:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json={"message": "Plan tomorrow's vendor meeting."})
            self.assertEqual(response.status_code, 401)

    def test_admin_can_create_users(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        for role in ["admin", "finance_manager", "it_manager", "employee"]:
            response = client.post(
                "/api/users",
                json={
                    "name": f"New {role.replace('_', ' ').title()}",
                    "email": f"new.{role}@example.com",
                    "password": "password123",
                    "role": role,
                },
                headers=headers,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["user"]["role"], role)

    def test_admin_can_edit_users_and_roles(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        created = client.post(
            "/api/users",
            json={
                "name": "Role Change User",
                "email": "role.change@example.com",
                "password": "password123",
                "role": "employee",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        user_id = created.json()["user"]["id"]

        updated = client.patch(
            f"/api/users/{user_id}",
            json={
                "name": "Updated Role User",
                "email": "updated.role@example.com",
                "role": "it_manager",
                "enabled": False,
            },
            headers=headers,
        )

        self.assertEqual(updated.status_code, 200)
        user = updated.json()["user"]
        self.assertEqual(user["name"], "Updated Role User")
        self.assertEqual(user["email"], "updated.role@example.com")
        self.assertEqual(user["role"], "it_manager")
        self.assertFalse(user["enabled"])

    def test_admin_can_edit_user_with_display_role_label(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        created = client.post(
            "/api/users",
            json={
                "name": "Display Role User",
                "email": "display.role@example.com",
                "password": "password123",
                "role": "Employee",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        user_id = created.json()["user"]["id"]

        updated = client.patch(
            f"/api/users/{user_id}",
            json={"name": "Display Role Updated", "role": "IT Manager"},
            headers=headers,
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["user"]["role"], "it_manager")

    def test_admin_can_delete_created_user(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        created = client.post(
            "/api/users",
            json={
                "name": "Delete Me",
                "email": "delete.me@example.com",
                "password": "password123",
                "role": "employee",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        user_id = created.json()["user"]["id"]

        deleted = client.delete(f"/api/users/{user_id}", headers=headers)
        users = client.get("/api/users", headers=headers).json()["users"]

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["user"]["email"], "delete.me@example.com")
        self.assertFalse(any(user["id"] == user_id for user in users))

    def test_admin_cannot_delete_own_account(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        admin_user = client.get("/api/auth/me", headers=headers).json()["user"]

        response = client.delete(f"/api/users/{admin_user['id']}", headers=headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot delete your own account", response.json()["detail"])

    def test_non_admin_cannot_edit_users(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        users = client.get("/api/users", headers=admin_headers).json()["users"]
        target = next(user for user in users if user["email"] == "employee@company.com")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.patch(
            f"/api/users/{target['id']}",
            json={"role": "admin"},
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_delete_users(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        users = client.get("/api/users", headers=admin_headers).json()["users"]
        target = next(user for user in users if user["email"] == "employee@company.com")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.delete(f"/api/users/{target['id']}", headers=employee_headers)

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_create_privileged_users(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/users",
            json={
                "name": "New Finance",
                "email": "new.finance@example.com",
                "password": "finance456",
                "role": "finance_manager",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_all_approval_types(self):
        client, app = self.api_client()
        admin_headers = self.auth_headers(client)

        for approval_type in [
            "external_vendor_email",
            "expense_approval",
            "payment",
            "invoice_mismatch",
            "it_support",
            "device_request",
            "travel_booking",
            "floor_activity",
            "file_deletion",
            "policy_exception",
        ]:
            approval = self.add_mock_approval(app, approval_type)
            response = client.patch(
                f"/api/approvals/{approval['id']}",
                json={"action": "approve_send"},
                headers=admin_headers,
            )
            self.assertEqual(response.status_code, 200)

    def test_admin_can_approve_vendor_followup(self):
        client, app = self.api_client()
        admin_headers = self.auth_headers(client)
        run = client.post(
            "/api/chat/command",
            json={"message": "Plan tomorrow's vendor review meeting."},
            headers=admin_headers,
        )
        self.assertEqual(run.status_code, 200)
        approval_id = run.json()["approval"]["id"]
        reviewer_headers = self.auth_headers(client)

        response = client.patch(
            f"/api/approvals/{approval_id}",
            json={"action": "approve_send"},
            headers=reviewer_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["approval"]["status"], "sent")

    def test_finance_cannot_approve_vendor_followup(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        run = client.post(
            "/api/chat/command",
            json={"message": "Plan tomorrow's vendor review meeting."},
            headers=admin_headers,
        )
        approval_id = run.json()["approval"]["id"]
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        response = client.patch(
            f"/api/approvals/{approval_id}",
            json={"action": "approve_send"},
            headers=finance_headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Admin approval", response.json()["detail"])

    def test_finance_manager_can_approve_finance_approval_types(self):
        client, app = self.api_client()
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        for approval_type in ["expense_approval", "payment", "invoice_mismatch", "reimbursement"]:
            approval = self.add_mock_approval(app, approval_type)
            response = client.patch(
                f"/api/approvals/{approval['id']}",
                json={"action": "approve_send"},
                headers=finance_headers,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["approval"]["status"], "sent")

    def test_approval_list_is_scoped_by_role(self):
        client, app = self.api_client()
        finance_approval = self.add_mock_approval(app, "payment")
        it_approval = self.add_mock_approval(app, "password_request")
        vendor_approval = self.add_mock_approval(app, "external_vendor_email")
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        finance_ids = {item["id"] for item in client.get("/api/approvals", headers=finance_headers).json()["approvals"]}
        it_ids = {item["id"] for item in client.get("/api/approvals", headers=it_headers).json()["approvals"]}
        employee_ids = {item["id"] for item in client.get("/api/approvals", headers=employee_headers).json()["approvals"]}

        self.assertIn(finance_approval["id"], finance_ids)
        self.assertNotIn(it_approval["id"], finance_ids)
        self.assertNotIn(vendor_approval["id"], finance_ids)
        self.assertIn(it_approval["id"], it_ids)
        self.assertNotIn(finance_approval["id"], it_ids)
        self.assertFalse(employee_ids)

    def test_it_manager_can_approve_it_approval_types(self):
        client, app = self.api_client()
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        for approval_type in ["it_support", "account_access", "device_request", "password_request"]:
            approval = self.add_mock_approval(app, approval_type)
            response = client.patch(
                f"/api/approvals/{approval['id']}",
                json={"action": "approve_send"},
                headers=it_headers,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["approval"]["status"], "sent")

    def test_it_manager_cannot_approve_finance_approvals(self):
        client, app = self.api_client()
        approval = self.add_mock_approval(app, "expense_approval")
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        response = client.patch(
            f"/api/approvals/{approval['id']}",
            json={"action": "approve_send"},
            headers=it_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_admin_approval_types(self):
        client, app = self.api_client()
        admin_headers = self.auth_headers(client)

        for approval_type in ["external_vendor_email", "travel_booking", "floor_activity"]:
            approval = self.add_mock_approval(app, approval_type)
            response = client.patch(
                f"/api/approvals/{approval['id']}",
                json={"action": "approve_send"},
                headers=admin_headers,
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["approval"]["status"], "sent")

    def test_employee_cannot_approve_payment(self):
        client, app = self.api_client()
        approval = self.add_mock_approval(app, "payment")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.patch(
            f"/api/approvals/{approval['id']}",
            json={"action": "approve_send"},
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_approve_sensitive_action(self):
        client, app = self.api_client()
        approval = self.add_mock_approval(app, "expense_approval")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.patch(
            f"/api/approvals/{approval['id']}",
            json={"action": "approve_send"},
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_can_create_and_view_own_expense(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        response = client.post(
            "/api/expenses",
            json=self.expense_payload(employee_name="Someone Else", employee_email="other@example.com"),
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 200)
        expense = response.json()["expense"]
        self.assertEqual(expense["employee_email"], "employee@company.com")
        self.assertEqual(expense["status"], "Pending Approval")
        self.assertIn("Amount over policy limit", expense["policy_exceptions"])

        list_response = client.get("/api/expenses", headers=employee_headers)
        self.assertEqual(list_response.status_code, 200)
        expense_ids = {item["id"] for item in list_response.json()["expenses"]}
        self.assertIn(expense["id"], expense_ids)

    def test_finance_manager_can_approve_expense(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        expense = client.post(
            "/api/expenses",
            json=self.expense_payload(),
            headers=employee_headers,
        ).json()["expense"]

        response = client.patch(
            f"/api/expenses/{expense['id']}/status",
            json={"status": "Approved"},
            headers=finance_headers,
        )

        self.assertEqual(response.status_code, 200)
        approved = response.json()["expense"]
        self.assertEqual(approved["status"], "Approved")
        self.assertEqual(approved["approved_by"], "Finance Manager")

    def test_employee_cannot_approve_expense(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        expense = client.post(
            "/api/expenses",
            json=self.expense_payload(),
            headers=employee_headers,
        ).json()["expense"]

        response = client.patch(
            f"/api/expenses/{expense['id']}/status",
            json={"status": "Approved"},
            headers=employee_headers,
        )

        self.assertEqual(response.status_code, 403)

    def test_expense_list_is_role_scoped(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        it_headers = self.auth_headers(client, "it@company.com", "it123")

        admin_expenses = client.get("/api/expenses", headers=admin_headers).json()["expenses"]
        employee_expenses = client.get("/api/expenses", headers=employee_headers).json()["expenses"]
        it_expenses = client.get("/api/expenses", headers=it_headers).json()["expenses"]

        self.assertGreaterEqual(len(admin_expenses), len(employee_expenses))
        self.assertTrue(all(item["employee_email"] == "employee@company.com" for item in employee_expenses))
        self.assertTrue(all(item["department"] == "IT" or item["category"] in {"Software", "Internet / Phone"} for item in it_expenses))

    def test_expense_import_preview_accepts_csv_and_reports_warnings(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        csv_content = (
            "expense_id,employee_name,employee_email,department,category,vendor_or_merchant,amount,currency,"
            "expense_date,payment_mode,receipt_status,receipt_attachment_name,notes,status,approval_required\n"
            "EXP-IMPORT-CSV-1001,Asha Rao,asha@example.com,Finance,Unknown Category,Metro Cabs,1250.50,INR,"
            "08/05/2026,UPI,Attached,receipt-1001.pdf,Client visit,Submitted,true\n"
        ).encode("utf-8")

        response = client.post(
            "/api/expenses/import/preview",
            json=self.inventory_import_payload("expenses.csv", csv_content),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview["file_type"], "csv")
        self.assertEqual(len(preview["rows"]), 1)
        expense = preview["rows"][0]["expense"]
        self.assertEqual(expense["expense_id"], "EXP-IMPORT-CSV-1001")
        self.assertEqual(expense["category"], "Miscellaneous")
        self.assertEqual(expense["expense_date"], "2026-05-08")
        self.assertTrue(expense["approval_required"])
        self.assertTrue(preview["warnings"])
        self.assertFalse(preview["errors"])

    def test_expense_import_preview_accepts_xlsx(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        rows = [
            [
                "expense_id",
                "employee_name",
                "employee_email",
                "department",
                "category",
                "vendor_or_merchant",
                "amount",
                "currency",
                "expense_date",
                "payment_mode",
                "receipt_status",
                "receipt_attachment_name",
                "notes",
                "status",
                "approval_required",
            ],
            [
                "EXP-IMPORT-XLSX-1001",
                "Jordan Lee",
                "jordan@example.com",
                "IT",
                "Software",
                "SaaS Vendor",
                "4500",
                "INR",
                "2026-05-08",
                "Corporate Card",
                "Pending",
                "",
                "License renewal",
                "Pending Approval",
                "false",
            ],
        ]

        response = client.post(
            "/api/expenses/import/preview",
            json=self.inventory_import_payload("expenses.xlsx", self.make_xlsx(rows)),
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview["file_type"], "xlsx")
        self.assertEqual(preview["rows"][0]["expense"]["expense_id"], "EXP-IMPORT-XLSX-1001")
        self.assertEqual(preview["rows"][0]["expense"]["category"], "Software")
        self.assertFalse(preview["errors"])

    def test_finance_manager_can_confirm_expense_import(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")
        items = [
            {
                **self.expense_payload(
                    employee_name="Imported User",
                    employee_email="imported@example.com",
                    department="Finance",
                    category="Food",
                    vendor_merchant="Cafe Vendor",
                    amount=640,
                    expense_date="2026-05-08",
                    status="Submitted",
                    approval_required=False,
                ),
                "expense_id": "EXP-IMPORT-CONFIRM-1001",
            }
        ]

        response = client.post(
            "/api/expenses/import/confirm",
            json={"filename": "expenses.csv", "items": items},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["import"]["successful_rows"], 1)
        self.assertEqual(payload["expenses"][0]["expense_id"], "EXP-IMPORT-CONFIRM-1001")
        listed = client.get("/api/expenses", headers=headers).json()["expenses"]
        self.assertIn("EXP-IMPORT-CONFIRM-1001", {expense["expense_id"] for expense in listed})
        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        import_log = next(log for log in logs if log["action"] == "expense.imported")
        self.assertEqual(import_log["details"]["file_name"], "expenses.csv")
        self.assertEqual(import_log["details"]["imported_count"], 1)

    def test_employee_cannot_import_expenses(self):
        client, _ = self.api_client()
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        csv_content = (
            "expense_id,employee_name,employee_email,department,category,amount,expense_date,status\n"
            "EXP-BLOCKED-1001,Employee User,employee@company.com,Operations,Food,300,2026-05-08,Submitted\n"
        ).encode("utf-8")

        preview = client.post(
            "/api/expenses/import/preview",
            json=self.inventory_import_payload("expenses.csv", csv_content),
            headers=employee_headers,
        )
        confirm = client.post(
            "/api/expenses/import/confirm",
            json={"filename": "expenses.csv", "items": [{**self.expense_payload(), "expense_id": "EXP-BLOCKED-1001"}]},
            headers=employee_headers,
        )

        self.assertEqual(preview.status_code, 403)
        self.assertEqual(confirm.status_code, 403)

    def test_expense_import_preview_reports_missing_columns_and_invalid_rows(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)
        missing_columns = "employee_name,amount\nAsha,not-a-number\n".encode("utf-8")
        invalid_row = (
            "expense_id,employee_name,employee_email,department,category,amount,expense_date,status\n"
            "EXP-BAD-1001,Asha,asha@example.com,Finance,Food,-5,not-a-date,Submitted\n"
        ).encode("utf-8")

        missing_response = client.post(
            "/api/expenses/import/preview",
            json=self.inventory_import_payload("wrong-expenses.csv", missing_columns),
            headers=headers,
        )
        invalid_response = client.post(
            "/api/expenses/import/preview",
            json=self.inventory_import_payload("bad-expenses.csv", invalid_row),
            headers=headers,
        )

        self.assertEqual(missing_response.status_code, 200)
        self.assertEqual(
            missing_response.json()["errors"],
            ["This file does not match the expense import template. Please use the expected expense columns."],
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertIn("Row 2: Amount must be numeric and greater than 0", invalid_response.json()["errors"])
        self.assertIn("Row 2: Expense date must be valid", invalid_response.json()["errors"])

    def test_travel_calendar_endpoints_seed_data_for_admin_and_finance(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")

        travel_response = client.get("/api/travel", headers=admin_headers)
        calendar_response = client.get("/api/calendar-events", headers=finance_headers)
        summary_response = client.get("/api/travel/summary", headers=admin_headers)

        self.assertEqual(travel_response.status_code, 200)
        self.assertGreaterEqual(len(travel_response.json()["travel_records"]), 4)
        self.assertEqual(calendar_response.status_code, 200)
        self.assertGreaterEqual(len(calendar_response.json()["calendar_events"]), 3)
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn("cards", summary_response.json())
        self.assertIn("travel_spend_by_department", summary_response.json())

    def test_it_and_employee_cannot_access_travel_calendar(self):
        client, _ = self.api_client()
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")

        self.assertEqual(client.get("/api/travel", headers=it_headers).status_code, 403)
        self.assertEqual(client.get("/api/calendar-events", headers=employee_headers).status_code, 403)
        self.assertEqual(client.get("/api/travel/summary", headers=it_headers).status_code, 403)

    def test_admin_can_create_and_update_travel_record_with_audit_logs(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        created = client.post("/api/travel", json=self.travel_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        record = created.json()["travel_record"]
        self.assertEqual(record["travel_id"], "TRV-TEST-1001")
        self.assertEqual(record["google_sync_status"], "Not Synced")

        updated = client.put(
            f"/api/travel/{record['id']}",
            json=self.travel_payload(actual_spend=30100, policy_status="Over Budget"),
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["travel_record"]["actual_spend"], 30100.0)
        self.assertEqual(updated.json()["travel_record"]["policy_status"], "Over Budget")

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        actions = {log["action"] for log in logs}
        self.assertIn("travel.created", actions)
        self.assertIn("travel.updated", actions)

    def test_finance_can_create_and_update_calendar_event_with_audit_logs(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client, "finance@company.com", "finance123")

        created = client.post("/api/calendar-events", json=self.calendar_event_payload(), headers=headers)
        self.assertEqual(created.status_code, 200)
        event = created.json()["calendar_event"]
        self.assertEqual(event["event_id"], "CAL-TEST-1001")
        self.assertEqual(event["google_sync_status"], "Not Synced")

        updated = client.put(
            f"/api/calendar-events/{event['id']}",
            json=self.calendar_event_payload(status="Tentative", title="Updated travel planning"),
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["calendar_event"]["status"], "Tentative")

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        actions = {log["action"] for log in logs}
        self.assertIn("calendar_event.created", actions)
        self.assertIn("calendar_event.updated", actions)

    def test_report_import_download_export_delete_for_admin(self):
        client, _ = self.api_client()
        headers = self.auth_headers(client)

        imported = client.post(
            "/api/reports/import",
            json=self.report_import_payload(
                report_name="Admin Export Test",
                report_type="Operations",
                department="Admin",
                filename="admin-export-test.csv",
                content=b"name,total\nadmin,10\n",
            ),
            headers=headers,
        )
        self.assertEqual(imported.status_code, 200)
        report = imported.json()["report"]
        self.assertEqual(report["file_type"], "CSV")
        self.assertEqual(report["uploaded_by_email"], "admin@company.com")

        list_response = client.get("/api/reports", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(any(item["id"] == report["id"] for item in list_response.json()["reports"]))

        download = client.get(f"/api/reports/{report['id']}/download", headers=headers)
        self.assertEqual(download.status_code, 200)
        self.assertIn("admin,10", download.text)

        exported = client.get(
            "/api/reports/export?department=Admin&file_type=CSV",
            headers=headers,
        )
        self.assertEqual(exported.status_code, 200)
        self.assertIn("Admin Export Test", exported.text)

        deleted = client.delete(f"/api/reports/{report['id']}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["report"]["report_id"], report["report_id"])

        logs = client.get("/api/audit-log", headers=headers).json()["audit_logs"]
        actions = {log["action"] for log in logs}
        self.assertIn("report.imported", actions)
        self.assertIn("report.exported", actions)
        self.assertIn("report.deleted", actions)

    def test_report_permissions_scope_it_finance_and_employee(self):
        client, _ = self.api_client()
        it_headers = self.auth_headers(client, "it@company.com", "it123")
        finance_headers = self.auth_headers(client, "finance@company.com", "finance123")
        employee_headers = self.auth_headers(client, "employee@company.com", "employee123")
        admin_headers = self.auth_headers(client)

        it_reports = client.get("/api/reports", headers=it_headers)
        finance_reports = client.get("/api/reports", headers=finance_headers)

        self.assertEqual(it_reports.status_code, 200)
        self.assertTrue(it_reports.json()["reports"])
        self.assertTrue(all(report["department"] == "IT" for report in it_reports.json()["reports"]))
        self.assertEqual(finance_reports.status_code, 200)
        self.assertTrue(finance_reports.json()["reports"])
        self.assertTrue(all(report["department"] == "Finance" for report in finance_reports.json()["reports"]))

        it_import = client.post(
            "/api/reports/import",
            json=self.report_import_payload(
                report_name="IT Security Report",
                report_type="IT",
                department="IT",
                filename="it-security.pdf",
                content=b"%PDF-1.4\nIT report\n",
            ),
            headers=it_headers,
        )
        blocked_it_import = client.post(
            "/api/reports/import",
            json=self.report_import_payload(
                report_name="Blocked Finance Report",
                report_type="Finance",
                department="Finance",
                filename="blocked-finance.csv",
            ),
            headers=it_headers,
        )
        employee_import = client.post(
            "/api/reports/import",
            json=self.report_import_payload(),
            headers=employee_headers,
        )
        employee_export = client.get("/api/reports/export", headers=employee_headers)

        self.assertEqual(it_import.status_code, 200)
        self.assertEqual(it_import.json()["report"]["file_type"], "PDF")
        self.assertEqual(blocked_it_import.status_code, 403)
        self.assertEqual(employee_import.status_code, 403)
        self.assertEqual(employee_export.status_code, 403)

        report_id = it_import.json()["report"]["id"]
        finance_delete = client.delete(f"/api/reports/{report_id}", headers=finance_headers)
        employee_download = client.get(f"/api/reports/{report_id}/download", headers=employee_headers)
        admin_delete = client.delete(f"/api/reports/{report_id}", headers=admin_headers)

        self.assertEqual(finance_delete.status_code, 403)
        self.assertEqual(employee_download.status_code, 403)
        self.assertEqual(admin_delete.status_code, 200)

    def test_audit_log_records_approver_identity(self):
        client, _ = self.api_client()
        admin_headers = self.auth_headers(client)
        run = client.post(
            "/api/chat/command",
            json={"message": "Plan tomorrow's vendor review meeting."},
            headers=admin_headers,
        )
        approval_id = run.json()["approval"]["id"]
        reviewer_headers = self.auth_headers(client)
        response = client.patch(
            f"/api/approvals/{approval_id}",
            json={"action": "approve_send"},
            headers=reviewer_headers,
        )
        self.assertEqual(response.status_code, 200)

        logs = client.get("/api/audit-log", headers=reviewer_headers).json()["audit_logs"]
        sent_log = next(log for log in logs if log["action"] == "external_email.sent")
        self.assertEqual(sent_log["actor"], "admin@company.com")
        self.assertEqual(sent_log["details"]["actor_role"], "admin")


if __name__ == "__main__":
    unittest.main()
