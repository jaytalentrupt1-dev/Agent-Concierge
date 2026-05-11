from copy import deepcopy
from datetime import date, datetime, time, timedelta


EMPLOYEES = [
    {
        "id": "emp-001",
        "name": "Maya Patel",
        "email": "maya.patel@example.com",
        "role": "Admin Operations Lead",
        "timezone": "America/New_York",
    },
    {
        "id": "emp-002",
        "name": "Priya Shah",
        "email": "priya.shah@example.com",
        "role": "Procurement Manager",
        "timezone": "America/New_York",
    },
    {
        "id": "emp-003",
        "name": "Ravi Menon",
        "email": "ravi.menon@example.com",
        "role": "IT Service Owner",
        "timezone": "America/New_York",
    },
    {
        "id": "emp-004",
        "name": "Elena Brooks",
        "email": "elena.brooks@example.com",
        "role": "Finance Controller",
        "timezone": "America/New_York",
    },
]


VENDOR = {
    "id": "vendor-acme",
    "name": "Acme Facilities Cloud",
    "contact_name": "Jordan Lee",
    "contact_email": "jordan.lee@acmefacilities.example",
    "service": "Workplace maintenance ticketing platform",
    "renewal_date": "2026-06-30",
    "risk_level": "medium",
}


FILES = [
    {
        "id": "file-001",
        "name": "Q2 SLA Scorecard.pdf",
        "type": "scorecard",
        "path": "/mock-files/vendor/q2-sla-scorecard.pdf",
        "sensitivity": "internal",
        "purpose": "Review uptime, response times, and missed tickets.",
    },
    {
        "id": "file-002",
        "name": "Open Incidents Export.csv",
        "type": "incident-export",
        "path": "/mock-files/vendor/open-incidents-export.csv",
        "sensitivity": "internal",
        "purpose": "Check aging unresolved tickets and escalation patterns.",
    },
    {
        "id": "file-003",
        "name": "Acme Contract Summary.docx",
        "type": "contract-summary",
        "path": "/mock-files/vendor/acme-contract-summary.docx",
        "sensitivity": "confidential",
        "purpose": "Confirm renewal window, SLA terms, and termination notice.",
    },
]


TRANSCRIPT = """
Maya: Thanks everyone. The goal is to decide if Acme is on track for renewal and what we need before the next monthly review.
Priya: The scorecard shows 96.8 percent SLA compliance against the contracted 97.5 percent. Most misses are after-hours HVAC tickets.
Ravi: Acme acknowledged the after-hours gap. They can add weekend dispatch coverage, but they need two weeks to confirm staffing.
Elena: The invoice trend is acceptable, but credits for missed SLA events have not been applied consistently.
Jordan: We can deliver a written remediation plan by Friday and include staffing coverage, credit reconciliation, and escalation owners.
Maya: Decision: continue the renewal review, but do not approve expansion until SLA compliance is back above 97.5 percent and credits are reconciled.
Priya: I will own the remediation plan request and ask Acme to send it by Friday.
Ravi: I will verify the weekend escalation path and update the incident runbook by next Tuesday.
Elena: I will review missed-SLA credits against the last two invoices by Monday.
Maya: Follow up externally with Jordan, summarizing the decisions and action items. Keep it factual and request the remediation plan by Friday.
"""


def _tomorrow_at(hour: int, minute: int = 0) -> str:
    target = date.today() + timedelta(days=1)
    return datetime.combine(target, time(hour=hour, minute=minute)).isoformat()


def mock_calendar_events() -> list[dict]:
    tomorrow = date.today() + timedelta(days=1)
    return [
        {
            "id": "cal-001",
            "title": "Facilities weekly sync",
            "start": datetime.combine(tomorrow, time(hour=9)).isoformat(),
            "end": datetime.combine(tomorrow, time(hour=9, minute=30)).isoformat(),
            "attendees": ["maya.patel@example.com", "ravi.menon@example.com"],
        },
        {
            "id": "cal-002",
            "title": "Finance close checkpoint",
            "start": datetime.combine(tomorrow, time(hour=13)).isoformat(),
            "end": datetime.combine(tomorrow, time(hour=14)).isoformat(),
            "attendees": ["elena.brooks@example.com"],
        },
    ]


def get_mock_context() -> dict:
    return {
        "employees": deepcopy(EMPLOYEES),
        "vendor": deepcopy(VENDOR),
        "files": deepcopy(FILES),
        "calendar_events": mock_calendar_events(),
        "meeting_transcript": TRANSCRIPT.strip(),
        "suggested_meeting_start": _tomorrow_at(10),
    }
