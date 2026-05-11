from __future__ import annotations

from datetime import date, timedelta


class MockAdminAI:
    mode = "mock"

    def generate_agenda(self, *, vendor: dict, files: list[dict]) -> list[dict]:
        return [
            {
                "time": "00:00-00:05",
                "topic": "Confirm renewal review goal and current vendor risk",
                "owner": "Maya Patel",
            },
            {
                "time": "00:05-00:20",
                "topic": "Review SLA scorecard and open incident export",
                "owner": "Priya Shah",
            },
            {
                "time": "00:20-00:35",
                "topic": "Discuss after-hours support gap and escalation path",
                "owner": "Ravi Menon",
            },
            {
                "time": "00:35-00:45",
                "topic": "Confirm invoice credits and renewal constraints",
                "owner": "Elena Brooks",
            },
            {
                "time": "00:45-00:55",
                "topic": f"Agree Acme follow-ups and owner deadlines",
                "owner": "Maya Patel",
            },
        ]

    def generate_reminder(
        self,
        *,
        meeting: dict,
        attendees: list[dict],
        files: list[dict],
    ) -> str:
        attendee_names = ", ".join([person["name"] for person in attendees])
        file_names = ", ".join([item["name"] for item in files])
        return (
            f"Reminder: {meeting['title']} is scheduled for {meeting['scheduled_for']}. "
            f"Attendees: {attendee_names}. Please review: {file_names}."
        )

    def summarize_transcript(self, transcript: str) -> str:
        return (
            "Acme is below the contracted SLA target because after-hours HVAC tickets are missing response windows. "
            "The team agreed to continue renewal review but pause expansion until compliance improves and SLA credits are reconciled. "
            "Acme will provide a remediation plan by Friday, while internal owners verify escalation coverage and invoice credits."
        )

    def extract_decisions(self, notes: str) -> list[dict]:
        return [
            {
                "decision": "Continue renewal review but do not approve expansion yet.",
                "reason": "SLA compliance is below the 97.5 percent threshold.",
            },
            {
                "decision": "Require Acme to provide a remediation plan by Friday.",
                "reason": "After-hours coverage and credit reconciliation need clear owners and dates.",
            },
            {
                "decision": "Reconcile missed-SLA invoice credits before renewal recommendation.",
                "reason": "Credits have not been applied consistently.",
            },
        ]

    def extract_action_items(self, notes: str, employees: list[dict]) -> list[dict]:
        lookup = {employee["name"]: employee for employee in employees}
        today = date.today()
        return [
            {
                "title": "Request Acme remediation plan covering staffing, credits, and escalation owners.",
                "owner_name": "Priya Shah",
                "owner_email": lookup["Priya Shah"]["email"],
                "due_date": (today + timedelta(days=2)).isoformat(),
            },
            {
                "title": "Verify weekend escalation path and update the incident runbook.",
                "owner_name": "Ravi Menon",
                "owner_email": lookup["Ravi Menon"]["email"],
                "due_date": (today + timedelta(days=7)).isoformat(),
            },
            {
                "title": "Review missed-SLA credits against the last two invoices.",
                "owner_name": "Elena Brooks",
                "owner_email": lookup["Elena Brooks"]["email"],
                "due_date": (today + timedelta(days=5)).isoformat(),
            },
        ]

    def draft_followup_email(
        self,
        *,
        vendor: dict,
        meeting: dict,
        decisions: list[dict],
        action_items: list[dict],
    ) -> dict:
        decision_lines = "\n".join([f"- {item['decision']}" for item in decisions])
        action_lines = "\n".join(
            [
                f"- {item['title']} Owner: {item['owner_name']}. Due: {item['due_date']}."
                for item in action_items
            ]
        )
        subject = f"Follow-up: {vendor['name']} vendor review"
        body = (
            f"Hi {vendor['contact_name']},\n\n"
            f"Thank you for joining the vendor review meeting on {meeting['scheduled_for']}.\n\n"
            "Decisions:\n"
            f"{decision_lines}\n\n"
            "Action items:\n"
            f"{action_lines}\n\n"
            "Please send the written remediation plan by Friday, including staffing coverage, "
            "SLA credit reconciliation, and escalation owners.\n\n"
            "Best,\n"
            "Maya"
        )
        return {"subject": subject, "body": body}


class OpenAIResponsesAI(MockAdminAI):
    mode = "openai_responses_with_mock_fallback"

    def __init__(self, *, api_key: str, model: str):
        self.model = model
        self.client = None
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except Exception:
            self.client = None

    def _responses_text(self, prompt: str) -> str | None:
        if not self.client:
            return None
        try:
            response = self.client.responses.create(model=self.model, input=prompt)
            return getattr(response, "output_text", None)
        except Exception:
            return None

    def summarize_transcript(self, transcript: str) -> str:
        prompt = (
            "Summarize this vendor review transcript in 3 factual sentences. "
            "Avoid commitments that are not in the transcript.\n\n"
            f"{transcript}"
        )
        text = self._responses_text(prompt)
        return text.strip() if text else super().summarize_transcript(transcript)


def get_ai_service(settings) -> MockAdminAI:
    if settings.use_openai_ai and settings.openai_api_key:
        return OpenAIResponsesAI(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockAdminAI()
