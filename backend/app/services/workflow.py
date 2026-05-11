from app.data.mock_data import get_mock_context
from app.repositories.admin_repository import AdminRepository
from app.services.agent_planner import MockAdminAgentPlanner
from app.services.approval_rules import ApprovalRulesService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.mock_ai import MockAdminAI


class VendorReviewWorkflow:
    def __init__(
        self,
        *,
        repository: AdminRepository,
        audit: AuditService,
        approvals: ApprovalService,
        ai: MockAdminAI,
        planner: MockAdminAgentPlanner | None = None,
        rules: ApprovalRulesService | None = None,
    ):
        self.repository = repository
        self.audit = audit
        self.approvals = approvals
        self.ai = ai
        self.planner = planner or MockAdminAgentPlanner()
        self.rules = rules or ApprovalRulesService()

    def run(self, command: str, actor_user: dict | None = None) -> dict:
        run_id = self.repository.create_chat_run(command)
        actor = actor_user["email"] if actor_user else "user"
        actor_details = (
            {
                "actor_user_id": actor_user["id"],
                "actor_role": actor_user["role"],
                "actor_name": actor_user["name"],
            }
            if actor_user
            else {}
        )
        self.audit.record(
            "chat.command.received",
            "accepted",
            actor=actor,
            details={"run_id": run_id, "command": command, **actor_details},
        )

        agent_plan = self.planner.create_plan(command)
        planner_mode = getattr(self.planner, "last_mode", self.planner.mode)
        agent_plan_record = self.repository.add_agent_plan(
            run_id=run_id,
            planner_mode=planner_mode,
            plan=agent_plan,
        )
        route = self.rules.route_request(
            message=command,
            requester_user_id=actor_user["id"] if actor_user else None,
            task_type=self._routing_task_type(agent_plan["task_type"]),
        )
        route_record = self.repository.add_routed_request(message=command, route=route)
        self.audit.record(
            "agent.plan.created",
            "completed",
            approval_required=agent_plan["approval_required"],
            approval_reason=agent_plan["approval_reason"] or None,
            details={
                "run_id": run_id,
                "agent_plan_id": agent_plan_record["id"],
                "planner_mode": planner_mode,
                "task_type": agent_plan["task_type"],
                "automation_level": agent_plan["automation_level"],
                "risk_level": agent_plan["risk_level"],
            },
        )
        self.audit.record(
            "request.routed",
            route["status"],
            actor=actor,
            approval_required=route["approval_required"],
            approval_reason=route["approval_reason"] or None,
            details={
                "run_id": run_id,
                "routed_request_id": route_record["id"],
                "task_type": route["task_type"],
                "priority": route["priority"],
                "risk_level": route["risk_level"],
                "assigned_role": route["assigned_role"],
                "required_approval_roles": route["required_approval_roles"],
                **actor_details,
            },
        )
        if route["approval_required"]:
            self.audit.record(
                "approval.rule.applied",
                "pending_approval",
                actor=actor,
                approval_required=True,
                approval_reason=route["approval_reason"],
                details={
                    "run_id": run_id,
                    "routed_request_id": route_record["id"],
                    "approval_type": route["approval_type"],
                    "required_approval_roles": route["required_approval_roles"],
                    **actor_details,
                },
            )

        if not self._should_execute_vendor_review(command, agent_plan):
            summary = (
                f"Planned {agent_plan['task_type'].replace('_', ' ')} request with "
                f"{agent_plan['automation_level'].replace('_', ' ')} automation."
            )
            self.repository.update_chat_run(run_id, "planned", summary)
            self.audit.record(
                "workflow.planned_only",
                "completed",
                approval_required=agent_plan["approval_required"],
                approval_reason=agent_plan["approval_reason"] or None,
                details={"run_id": run_id, "agent_plan_id": agent_plan_record["id"]},
            )
            return {
                "run_id": run_id,
                "summary": summary,
                "execution_status": "planned_only",
                "agent_plan": agent_plan,
                "agent_plan_record": agent_plan_record,
                "route": route,
                "route_record": route_record,
                "dashboard": self.repository.dashboard(),
            }

        context = get_mock_context()
        employees = context["employees"]
        vendor = context["vendor"]
        files = context["files"]
        transcript = context["meeting_transcript"]

        attendees = employees + [
            {
                "id": vendor["id"],
                "name": vendor["contact_name"],
                "email": vendor["contact_email"],
                "role": f"{vendor['name']} vendor contact",
                "external": True,
            }
        ]

        agenda = self.ai.generate_agenda(vendor=vendor, files=files)
        self.audit.record(
            "agenda.prepared",
            "completed",
            details={"run_id": run_id, "agenda_items": len(agenda), "ai_mode": self.ai.mode},
        )

        meeting = self.repository.add_meeting(
            {
                "title": f"{vendor['name']} vendor review",
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "scheduled_for": context["suggested_meeting_start"],
                "status": "scheduled",
                "agenda": agenda,
                "attendees": attendees,
                "files": files,
            }
        )
        self.audit.record(
            "meeting.scheduled",
            "completed",
            details={
                "run_id": run_id,
                "meeting_id": meeting["id"],
                "scheduled_for": meeting["scheduled_for"],
            },
        )

        reminder = self.ai.generate_reminder(meeting=meeting, attendees=employees, files=files)
        meeting = self.repository.update_meeting(meeting["id"], reminder_message=reminder)
        self.audit.record(
            "reminder.generated",
            "completed",
            details={
                "run_id": run_id,
                "meeting_id": meeting["id"],
                "audience": "internal_attendees",
            },
        )

        notes = self.ai.summarize_transcript(transcript)
        self.audit.record(
            "meeting_notes.generated",
            "completed",
            details={"run_id": run_id, "meeting_id": meeting["id"], "ai_mode": self.ai.mode},
        )

        decisions = self.ai.extract_decisions(notes)
        self.audit.record(
            "decisions.extracted",
            "completed",
            details={"run_id": run_id, "meeting_id": meeting["id"], "decisions": len(decisions)},
        )

        action_items = self.ai.extract_action_items(notes, employees)
        tasks = [
            self.repository.add_task({**item, "meeting_id": meeting["id"]})
            for item in action_items
        ]
        self.audit.record(
            "action_items.created",
            "completed",
            details={"run_id": run_id, "meeting_id": meeting["id"], "tasks": len(tasks)},
        )

        note = self.repository.add_meeting_notes(
            {
                "meeting_id": meeting["id"],
                "transcript": transcript,
                "summary": notes,
                "decisions": decisions,
                "action_items": action_items,
            }
        )

        email = self.ai.draft_followup_email(
            vendor=vendor,
            meeting=meeting,
            decisions=decisions,
            action_items=action_items,
        )
        email_route = self.rules.apply_rule(
            task_type="vendor_management",
            approval_type="external_vendor_email",
            requester_user_id=actor_user["id"] if actor_user else None,
        ).to_dict()
        reason = email_route["approval_reason"]
        self.audit.record(
            "external_email.drafted",
            "needs_approval",
            approval_required=True,
            approval_reason=reason,
            details={
                "run_id": run_id,
                "meeting_id": meeting["id"],
                "recipient_email": vendor["contact_email"],
                "assigned_role": email_route["assigned_role"],
                "required_approval_roles": email_route["required_approval_roles"],
            },
        )
        approval = self.approvals.queue_external_email(
            recipient_name=vendor["contact_name"],
            recipient_email=vendor["contact_email"],
            subject=email["subject"],
            body=email["body"],
            related_meeting_id=meeting["id"],
            requester_user_id=actor_user["id"] if actor_user else None,
        )

        self.audit.record(
            "dashboard.updated",
            "completed",
            details={
                "run_id": run_id,
                "meeting_id": meeting["id"],
                "open_tasks": len(tasks),
                "pending_approval_id": approval["id"],
            },
        )

        summary = (
            f"Scheduled {meeting['title']}, prepared {len(files)} files, generated notes, "
            f"created {len(tasks)} action items, and queued the vendor follow-up email for approval."
        )
        self.repository.update_chat_run(run_id, "completed", summary)
        self.audit.record(
            "workflow.completed",
            "completed",
            details={"run_id": run_id, "meeting_id": meeting["id"]},
        )

        return {
            "run_id": run_id,
            "summary": summary,
            "execution_status": "completed",
            "agent_plan": agent_plan,
            "agent_plan_record": agent_plan_record,
            "route": route,
            "route_record": route_record,
            "meeting": meeting,
            "note": note,
            "decisions": decisions,
            "action_items": tasks,
            "approval": approval,
            "dashboard": self.repository.dashboard(),
        }

    def _should_execute_vendor_review(self, command: str, agent_plan: dict) -> bool:
        text = command.lower()
        return (
            agent_plan["task_type"] in {"vendor_management", "meeting_management"}
            and "vendor" in text
            and "meeting" in text
        )

    def _routing_task_type(self, planner_task_type: str) -> str | None:
        mapping = {
            "meeting_notes": "meeting_management",
            "reminder_management": "meeting_management",
            "task_tracking": "meeting_management",
            "approval_followup": "report_generation",
        }
        if planner_task_type in {
            "meeting_management",
            "vendor_management",
            "expense_management",
            "travel_management",
            "inventory_management",
            "document_management",
            "report_generation",
            "floor_activity_management",
        }:
            return planner_task_type
        return mapping.get(planner_task_type)
