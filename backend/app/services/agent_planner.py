from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.policy import safety_review


TaskType = Literal[
    "meeting_management",
    "reminder_management",
    "meeting_notes",
    "task_tracking",
    "document_management",
    "report_generation",
    "approval_followup",
    "inventory_management",
    "travel_management",
    "expense_management",
    "it_request",
    "floor_activity_management",
    "vendor_management",
]

AutomationLevel = Literal[
    "automatic",
    "needs_human_approval",
    "human_decision_required",
]

RiskLevel = Literal["low", "medium", "high", "critical"]


class AgentPlan(BaseModel):
    task_type: TaskType
    automation_level: AutomationLevel
    summary: str = Field(min_length=1, max_length=800)
    steps: list[str] = Field(min_length=1, max_length=12)
    required_tools: list[str] = Field(min_length=1, max_length=12)
    approval_required: bool
    approval_reason: str = Field(max_length=1200)
    risk_level: RiskLevel
    expected_outputs: list[str] = Field(min_length=1, max_length=12)


SYSTEM_PROMPT = """
You are an AI Admin Agent planning layer for an enterprise admin automation MVP.
Classify the user's request and return a structured execution plan. All external
systems are mocked. Do not claim that a real email, calendar event, payment,
booking, ticket, file action, or vendor API call will be executed.

Allowed task_type values:
- meeting_management
- reminder_management
- meeting_notes
- task_tracking
- document_management
- report_generation
- approval_followup
- inventory_management
- travel_management
- expense_management
- it_request
- floor_activity_management
- vendor_management

Allowed automation_level values:
- automatic
- needs_human_approval
- human_decision_required

Safety rules:
Human approval is required for external vendor emails, payments, expense
approvals, travel bookings, contract changes, confidential document sharing,
file deletion, legal/compliance decisions, emergency/safety decisions, and
policy exceptions. Legal/compliance, emergency/safety, policy exception, and
unknown high-risk requests should be human_decision_required.

Return practical mock-tool steps only. If the request is ambiguous or unrelated
to the allowed task types, choose the closest task type and require a human
decision. The required_tools field must list mocked tools only.
""".strip()


class MockAdminAgentPlanner:
    mode = "mock_agent_planner"

    def __init__(self):
        self.last_mode = self.mode

    def create_plan(self, command: str) -> dict:
        self.last_mode = self.mode
        task_type = self._classify(command)
        plan = {
            "task_type": task_type,
            "automation_level": "automatic",
            "summary": self._summary(command, task_type),
            "steps": self._steps(task_type),
            "required_tools": self._tools(task_type),
            "approval_required": False,
            "approval_reason": "",
            "risk_level": "low",
            "expected_outputs": self._expected_outputs(task_type),
        }
        return self._enforce_safety(plan, command)

    def _classify(self, command: str) -> str:
        text = command.lower()
        if any(term in text for term in ["vendor", "supplier", "renewal"]):
            return "vendor_management"
        if any(term in text for term in ["travel", "flight", "hotel", "trip"]):
            return "travel_management"
        if any(term in text for term in ["expense", "reimbursement", "payment", "invoice"]):
            return "expense_management"
        if any(term in text for term in ["password", "account access", "device", "it support", "laptop"]):
            return "it_request"
        if any(term in text for term in ["inventory", "stock", "asset count", "supplies"]):
            return "inventory_management"
        if any(term in text for term in ["floor", "workplace", "facility", "facilities"]):
            return "floor_activity_management"
        if any(term in text for term in ["delete file", "remove file", "document", "file"]):
            return "document_management"
        if any(term in text for term in ["report", "dashboard", "status update"]):
            return "report_generation"
        if any(term in text for term in ["notes", "minutes", "transcript"]):
            return "meeting_notes"
        if any(term in text for term in ["remind", "reminder", "notify"]):
            return "reminder_management"
        if any(term in text for term in ["task", "action item", "follow up", "follow-up"]):
            return "task_tracking"
        if any(term in text for term in ["meeting", "calendar", "schedule"]):
            return "meeting_management"
        if any(term in text for term in ["approve", "approval", "decision", "exception"]):
            return "approval_followup"
        return "approval_followup"

    def _summary(self, command: str, task_type: str) -> str:
        if task_type == "vendor_management":
            return "Plan a mocked vendor administration workflow and route any external vendor communication through approval."
        if task_type == "reminder_management":
            return "Prepare an internal reminder using mocked calendar and notification tools."
        if task_type == "expense_management":
            return "Review the expense or payment request and route risky financial action through human approval."
        if task_type == "document_management":
            return "Plan document handling with mocked file metadata and required approval for sensitive or destructive actions."
        if task_type == "it_request":
            return "Route the IT request through mocked support workflows and required IT approval when needed."
        if task_type == "approval_followup":
            return "Create a cautious admin plan and require a human decision when the request is ambiguous or high risk."
        return f"Create a mocked admin execution plan for {task_type.replace('_', ' ')}."

    def _steps(self, task_type: str) -> list[str]:
        base_steps = {
            "vendor_management": [
                "Read mocked vendor, employee, calendar, file, and transcript context.",
                "Prepare a meeting agenda and internal reminder.",
                "Generate notes, decisions, action items, and a vendor follow-up draft.",
                "Queue external vendor communication for human review before send.",
                "Write dashboard and audit updates.",
            ],
            "reminder_management": [
                "Read mocked calendar and recipient context.",
                "Draft the reminder message.",
                "Record the reminder event in the audit log.",
            ],
            "expense_management": [
                "Read mocked expense or payment details.",
                "Assess approval requirements and financial risk.",
                "Queue the request for human review before any financial action.",
            ],
            "document_management": [
                "Read mocked document metadata.",
                "Assess sensitivity and destructive-action risk.",
                "Queue sensitive sharing or deletion for human review before action.",
            ],
            "it_request": [
                "Read mocked IT request context.",
                "Assess account, password, or device approval requirements.",
                "Route the request to IT Manager/Admin approval before action.",
            ],
            "approval_followup": [
                "Clarify the requested admin decision.",
                "Assess risk and policy constraints.",
                "Route the request to a human decision queue before execution.",
            ],
        }
        return base_steps.get(
            task_type,
            [
                "Classify the admin request.",
                "Select only mocked tools for planning.",
                "Record the plan and expected outputs.",
            ],
        )

    def _tools(self, task_type: str) -> list[str]:
        tools = {
            "vendor_management": [
                "mock_calendar",
                "mock_people_directory",
                "mock_file_context",
                "mock_meeting_transcript",
                "mock_task_tracker",
                "mock_email_drafts",
                "mock_approval_queue",
                "mock_audit_log",
            ],
            "reminder_management": ["mock_calendar", "mock_notifications", "mock_audit_log"],
            "meeting_notes": ["mock_meeting_transcript", "mock_notes", "mock_audit_log"],
            "task_tracking": ["mock_task_tracker", "mock_people_directory", "mock_audit_log"],
            "document_management": ["mock_file_context", "mock_approval_queue", "mock_audit_log"],
            "report_generation": ["mock_dashboard_data", "mock_reports", "mock_audit_log"],
            "approval_followup": ["mock_approval_queue", "mock_policy_rules", "mock_audit_log"],
            "inventory_management": ["mock_inventory", "mock_task_tracker", "mock_audit_log"],
            "travel_management": ["mock_travel_context", "mock_approval_queue", "mock_audit_log"],
            "expense_management": ["mock_expenses", "mock_approval_queue", "mock_audit_log"],
            "it_request": ["mock_it_service_desk", "mock_approval_queue", "mock_audit_log"],
            "floor_activity_management": ["mock_floor_activity", "mock_notifications", "mock_audit_log"],
        }
        return tools.get(task_type, ["mock_policy_rules", "mock_audit_log"])

    def _expected_outputs(self, task_type: str) -> list[str]:
        outputs = {
            "vendor_management": [
                "scheduled meeting",
                "agenda",
                "attached mock files",
                "internal reminder",
                "meeting notes",
                "decisions",
                "action items",
                "pending external email approval",
                "dashboard update",
                "audit log entries",
            ],
            "reminder_management": ["reminder draft", "audit log entry"],
            "expense_management": ["approval queue item", "audit log entry"],
            "document_management": ["document action plan", "approval queue item", "audit log entry"],
            "it_request": ["IT request route", "approval queue item", "audit log entry"],
            "approval_followup": ["human decision queue item", "audit log entry"],
        }
        return outputs.get(task_type, ["structured plan", "audit log entry"])

    def _enforce_safety(self, plan: dict, command: str) -> dict:
        review = safety_review(command)
        if not review["approval_required"]:
            if plan["automation_level"] not in {"automatic", "needs_human_approval", "human_decision_required"}:
                plan["automation_level"] = "automatic"
            return self._validated(plan)

        plan["approval_required"] = True
        plan["approval_reason"] = review["approval_reason"]
        plan["automation_level"] = (
            "human_decision_required"
            if review["human_decision_required"]
            else "needs_human_approval"
        )
        plan["risk_level"] = review["risk_level"]

        if "required_tools" not in plan and "required_mock_tools" in plan:
            plan["required_tools"] = plan.pop("required_mock_tools")

        if "mock_approval_queue" not in plan["required_tools"]:
            plan["required_tools"].append("mock_approval_queue")
        if plan["automation_level"] == "human_decision_required":
            if "mock_human_decision_queue" not in plan["required_tools"]:
                plan["required_tools"].append("mock_human_decision_queue")
            if "human decision queue item" not in plan["expected_outputs"]:
                plan["expected_outputs"].append("human decision queue item")

        return self._validated(plan)

    def _validated(self, plan: dict) -> dict:
        if "required_tools" not in plan and "required_mock_tools" in plan:
            plan["required_tools"] = plan.pop("required_mock_tools")
        return AgentPlan.model_validate(plan).model_dump()


class OpenAIResponsesAdminAgentPlanner(MockAdminAgentPlanner):
    mode = "openai_responses_agent_planner"

    def __init__(self, *, api_key: str, model: str):
        super().__init__()
        self.model = model
        self.client = None
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except Exception:
            self.client = None

    def create_plan(self, command: str) -> dict:
        raw_plan = self._responses_plan(command)
        if raw_plan is None:
            plan = super().create_plan(command)
            self.last_mode = "mock_agent_planner_fallback"
            return plan

        self.last_mode = self.mode
        return self._enforce_safety(raw_plan, command)

    def _responses_plan(self, command: str) -> dict | None:
        if not self.client:
            return None
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": command},
                ],
                text_format=AgentPlan,
            )
        except Exception:
            return None

        parsed = getattr(response, "output_parsed", None)
        if parsed:
            return parsed.model_dump()

        for output in getattr(response, "output", []):
            for item in getattr(output, "content", []):
                parsed = getattr(item, "parsed", None)
                if parsed:
                    return parsed.model_dump()

        return None


def get_agent_planner(settings) -> MockAdminAgentPlanner:
    api_key = getattr(settings, "openai_api_key", "")
    model = getattr(settings, "openai_model", "gpt-5.5")
    if api_key:
        return OpenAIResponsesAdminAgentPlanner(api_key=api_key, model=model)
    return MockAdminAgentPlanner()
