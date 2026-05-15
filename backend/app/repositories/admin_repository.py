from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.database import Database
from app.services.approval_rules import ApprovalRulesService


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _normalize_role_value(role: str) -> str:
    normalized = str(role or "").strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "it": "it_manager",
        "finance": "finance_manager",
        "operation": "employee",
        "it_manager": "it_manager",
        "finance_manager": "finance_manager",
        "admin": "admin",
        "employee": "employee",
    }.get(normalized, role)


def _normalize_assigned_role(role: str) -> str:
    return {
        "it": "it_manager",
        "finance": "finance_manager",
        "operation": "admin",
    }.get(role, role)


class AdminRepository:
    def __init__(self, database_path: str | Path):
        self.db = Database(database_path)
        self.report_upload_dir = self.db.path.parent / "uploads" / "reports"

    def init_schema(self) -> None:
        with self.db.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS agent_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    planner_mode TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    automation_level TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    approval_reason TEXT,
                    risk_level TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES chat_runs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    vendor_id TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agenda_json TEXT NOT NULL,
                    attendees_json TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    reminder_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meeting_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER NOT NULL,
                    transcript TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    decisions_json TEXT NOT NULL,
                    action_items_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    department TEXT NOT NULL,
                    assigned_to TEXT NOT NULL,
                    assigned_user_id INTEGER,
                    assigned_email TEXT NOT NULL DEFAULT '',
                    assigned_role TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    owner_email TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    meeting_id INTEGER,
                    created_by_user_id INTEGER,
                    created_by_name TEXT NOT NULL,
                    created_by_email TEXT NOT NULL,
                    created_by_role TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE SET NULL,
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY(assigned_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    approval_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_reason TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    original_body TEXT NOT NULL,
                    related_meeting_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sent_at TEXT,
                    cancelled_reason TEXT,
                    FOREIGN KEY(related_meeting_id) REFERENCES meetings(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS routed_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requester_user_id INTEGER,
                    assigned_role TEXT NOT NULL,
                    required_approval_roles_json TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    approval_reason TEXT,
                    approval_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(requester_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT NOT NULL,
                    contact_person TEXT NOT NULL,
                    email TEXT NOT NULL,
                    contact_details TEXT NOT NULL,
                    office_address TEXT NOT NULL,
                    service_provided TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    billing_amount INTEGER NOT NULL DEFAULT 0,
                    billing_cycle TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS tickets (
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
                    requester_role TEXT NOT NULL,
                    assigned_role TEXT NOT NULL,
                    assigned_team TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(requester_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT NOT NULL,
                    related_entity_type TEXT NOT NULL,
                    related_entity_id TEXT NOT NULL,
                    user_id INTEGER,
                    target_role TEXT NOT NULL,
                    read_user_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_id TEXT NOT NULL UNIQUE,
                    employee_user_id INTEGER,
                    employee_name TEXT NOT NULL,
                    employee_email TEXT NOT NULL,
                    employee_role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    category TEXT NOT NULL,
                    vendor_merchant TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    expense_date TEXT NOT NULL,
                    payment_mode TEXT NOT NULL,
                    receipt_status TEXT NOT NULL,
                    receipt_attachment_name TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    approved_by TEXT NOT NULL,
                    policy_exceptions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(employee_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS inventory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL UNIQUE,
                    item_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    serial_number TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    location TEXT NOT NULL,
                    assigned_to TEXT NOT NULL,
                    department TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    warranty_end_date TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    minimum_stock_level INTEGER NOT NULL,
                    employee_name TEXT NOT NULL DEFAULT '',
                    serial_no TEXT NOT NULL DEFAULT '',
                    model_no TEXT NOT NULL DEFAULT '',
                    ram TEXT NOT NULL DEFAULT '',
                    disk TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    import_batch_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(import_batch_id) REFERENCES inventory_import_batches(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS inventory_import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    imported_by_user_id INTEGER,
                    imported_by_name TEXT NOT NULL,
                    imported_by_email TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    total_rows INTEGER NOT NULL,
                    successful_rows INTEGER NOT NULL,
                    failed_rows INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    deleted_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(imported_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS travel_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    travel_id TEXT NOT NULL UNIQUE,
                    employee_name TEXT NOT NULL,
                    employee_email TEXT NOT NULL,
                    department TEXT NOT NULL,
                    destination_from TEXT NOT NULL,
                    destination_to TEXT NOT NULL,
                    travel_start_date TEXT NOT NULL,
                    travel_end_date TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    travel_mode TEXT NOT NULL,
                    estimated_budget REAL NOT NULL,
                    actual_spend REAL NOT NULL,
                    number_of_trips INTEGER NOT NULL,
                    approval_status TEXT NOT NULL,
                    policy_status TEXT NOT NULL,
                    booking_status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    google_calendar_event_id TEXT NOT NULL,
                    google_sync_status TEXT NOT NULL,
                    google_last_synced_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    start_datetime TEXT NOT NULL,
                    end_datetime TEXT NOT NULL,
                    location TEXT NOT NULL,
                    attendees TEXT NOT NULL,
                    related_travel_id TEXT NOT NULL,
                    reminder TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    status TEXT NOT NULL,
                    google_calendar_event_id TEXT NOT NULL,
                    google_sync_status TEXT NOT NULL,
                    google_last_synced_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL UNIQUE,
                    report_name TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    department TEXT NOT NULL,
                    uploaded_by_user_id INTEGER,
                    uploaded_by_name TEXT NOT NULL,
                    uploaded_by_email TEXT NOT NULL,
                    uploaded_by_role TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    stored_file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS connectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    connector_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    last_tested_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, connector_type),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS message_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    channel TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    module TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS communication_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    recipient_phone TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message_body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    related_module TEXT NOT NULL,
                    related_record_id TEXT NOT NULL,
                    sent_by_user_id INTEGER,
                    sent_by_name TEXT NOT NULL,
                    sent_by_email TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(sent_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approval_required INTEGER NOT NULL,
                    approval_reason TEXT,
                    details_json TEXT NOT NULL
                );
                """
            )
            self._ensure_vendor_columns(conn)
            self._ensure_user_columns(conn)
            self._ensure_task_columns(conn)
            self._ensure_ticket_columns(conn)
            self._ensure_expense_columns(conn)
            self._ensure_inventory_columns(conn)
            self._ensure_notification_columns(conn)
            self._ensure_travel_columns(conn)
            self._ensure_report_columns(conn)
            self._ensure_connector_tables(conn)

    def _ensure_user_columns(self, conn) -> None:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if not columns:
            return
        if "is_demo" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")

    def _ensure_vendor_columns(self, conn) -> None:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(vendors)").fetchall()
        }
        if not columns:
            return
        if "billing_amount" not in columns:
            conn.execute("ALTER TABLE vendors ADD COLUMN billing_amount INTEGER NOT NULL DEFAULT 0")

    def ensure_vendor_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_vendor_columns(conn)

    def _ensure_task_columns(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if not existing:
            return
        required_columns = {
            "task_id": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "category": "TEXT NOT NULL DEFAULT 'Admin'",
            "department": "TEXT NOT NULL DEFAULT 'Admin'",
            "assigned_to": "TEXT NOT NULL DEFAULT ''",
            "assigned_user_id": "INTEGER",
            "assigned_email": "TEXT NOT NULL DEFAULT ''",
            "assigned_role": "TEXT NOT NULL DEFAULT 'admin'",
            "priority": "TEXT NOT NULL DEFAULT 'Medium'",
            "created_by_user_id": "INTEGER",
            "created_by_name": "TEXT NOT NULL DEFAULT 'Agent Concierge'",
            "created_by_email": "TEXT NOT NULL DEFAULT 'system@agent.local'",
            "created_by_role": "TEXT NOT NULL DEFAULT 'admin'",
            "notes": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column} {definition}")
        rows = conn.execute("SELECT id, task_id, title, owner_name, owner_email, source, status FROM tasks").fetchall()
        for row in rows:
            task_id = row["task_id"] or f"TASK-{1000 + int(row['id'])}"
            category = "Vendor" if row["source"] == "meeting_action_item" else "Admin"
            assigned_to = row["owner_name"] or row["owner_email"] or "Admin Team"
            normalized_status = self._normalize_task_status(row["status"])
            conn.execute(
                """
                UPDATE tasks
                SET task_id = ?, description = COALESCE(NULLIF(description, ''), ?),
                    category = COALESCE(NULLIF(category, ''), ?),
                    department = COALESCE(NULLIF(department, ''), ?),
                    assigned_to = COALESCE(NULLIF(assigned_to, ''), ?),
                    assigned_email = COALESCE(NULLIF(assigned_email, ''), owner_email, ''),
                    assigned_role = COALESCE(NULLIF(assigned_role, ''), ?),
                    priority = COALESCE(NULLIF(priority, ''), ?),
                    status = ?
                WHERE id = ?
                """,
                (
                    task_id,
                    row["title"],
                    category,
                    "Admin",
                    assigned_to,
                    "admin",
                    "Medium",
                    normalized_status,
                    row["id"],
                ),
            )

    def ensure_task_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_task_columns(conn)

    def _ensure_ticket_columns(self, conn) -> None:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(tickets)").fetchall()
        }
        if not columns:
            return
        if "requester_role" not in columns:
            conn.execute("ALTER TABLE tickets ADD COLUMN requester_role TEXT NOT NULL DEFAULT ''")

    def ensure_ticket_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_ticket_columns(conn)

    def _ensure_expense_columns(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
        }
        if not existing:
            return
        required_columns = {
            "employee_role": "TEXT NOT NULL DEFAULT ''",
            "policy_exceptions_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in required_columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE expenses ADD COLUMN {column} {definition}")

    def ensure_expense_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_expense_columns(conn)

    def _ensure_inventory_columns(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(inventory_items)").fetchall()
        }
        if not existing:
            return
        required_columns = {
            "subcategory": "TEXT NOT NULL DEFAULT ''",
            "brand": "TEXT NOT NULL DEFAULT ''",
            "model": "TEXT NOT NULL DEFAULT ''",
            "serial_number": "TEXT NOT NULL DEFAULT ''",
            "assigned_to": "TEXT NOT NULL DEFAULT ''",
            "department": "TEXT NOT NULL DEFAULT ''",
            "purchase_date": "TEXT NOT NULL DEFAULT ''",
            "warranty_end_date": "TEXT NOT NULL DEFAULT ''",
            "vendor": "TEXT NOT NULL DEFAULT ''",
            "minimum_stock_level": "INTEGER NOT NULL DEFAULT 0",
            "employee_name": "TEXT NOT NULL DEFAULT ''",
            "serial_no": "TEXT NOT NULL DEFAULT ''",
            "model_no": "TEXT NOT NULL DEFAULT ''",
            "ram": "TEXT NOT NULL DEFAULT ''",
            "disk": "TEXT NOT NULL DEFAULT ''",
            "notes": "TEXT NOT NULL DEFAULT ''",
            "import_batch_id": "INTEGER",
        }
        for column, definition in required_columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE inventory_items ADD COLUMN {column} {definition}")

    def ensure_inventory_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_inventory_columns(conn)

    def _ensure_notification_columns(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(notifications)").fetchall()
        }
        if not existing:
            return
        required_columns = {
            "user_id": "INTEGER",
            "target_role": "TEXT NOT NULL DEFAULT ''",
            "read_user_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in required_columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE notifications ADD COLUMN {column} {definition}")

    def ensure_notification_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_notification_columns(conn)

    def _ensure_travel_columns(self, conn) -> None:
        travel_existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(travel_records)").fetchall()
        }
        travel_columns = {
            "google_calendar_event_id": "TEXT NOT NULL DEFAULT ''",
            "google_sync_status": "TEXT NOT NULL DEFAULT 'Not Synced'",
            "google_last_synced_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in travel_columns.items():
            if travel_existing and column not in travel_existing:
                conn.execute(f"ALTER TABLE travel_records ADD COLUMN {column} {definition}")

        event_existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(calendar_events)").fetchall()
        }
        event_columns = {
            "google_calendar_event_id": "TEXT NOT NULL DEFAULT ''",
            "google_sync_status": "TEXT NOT NULL DEFAULT 'Not Synced'",
            "google_last_synced_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in event_columns.items():
            if event_existing and column not in event_existing:
                conn.execute(f"ALTER TABLE calendar_events ADD COLUMN {column} {definition}")

    def ensure_travel_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_travel_columns(conn)

    def _ensure_report_columns(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(reports)").fetchall()
        }
        if not existing:
            return
        required_columns = {
            "file_size": "INTEGER NOT NULL DEFAULT 0",
            "notes": "TEXT NOT NULL DEFAULT ''",
            "uploaded_by_role": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE reports ADD COLUMN {column} {definition}")

    def ensure_report_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_report_columns(conn)

    def _ensure_connector_tables(self, conn) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS connectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                connector_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                display_name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                last_tested_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, connector_type),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS message_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                channel TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                module TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS communication_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                subject TEXT NOT NULL,
                message_body TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                related_module TEXT NOT NULL,
                related_record_id TEXT NOT NULL,
                sent_by_user_id INTEGER,
                sent_by_name TEXT NOT NULL,
                sent_by_email TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                error_message TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sent_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        self._migrate_connector_ownership(conn)

    def _migrate_connector_ownership(self, conn) -> None:
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(connectors)").fetchall()
        }
        if not existing or "user_id" in existing:
            return
        admin = conn.execute(
            "SELECT id FROM users WHERE email = ? OR role = ? ORDER BY id LIMIT 1",
            ("admin@company.com", "admin"),
        ).fetchone()
        owner_id = int(admin["id"]) if admin else 1
        conn.execute("ALTER TABLE connectors RENAME TO connectors_legacy")
        conn.executescript(
            """
            CREATE TABLE connectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                connector_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                display_name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                last_tested_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, connector_type),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            INSERT INTO connectors (
                user_id, connector_type, provider, status, display_name, config_json,
                last_tested_at, created_at, updated_at
            )
            SELECT ?, connector_type, provider, status, display_name, config_json,
                last_tested_at, created_at, updated_at
            FROM connectors_legacy
            """,
            (owner_id,),
        )
        conn.execute("DROP TABLE connectors_legacy")

    def ensure_connector_schema(self) -> None:
        with self.db.connection() as conn:
            self._ensure_connector_tables(conn)

    def reset(self) -> None:
        with self.db.connection() as conn:
            for table in [
                "notifications",
                "audit_logs",
                "approvals",
                "tasks",
                "meeting_notes",
                "meetings",
                "agent_plans",
                "routed_requests",
                "vendors",
                "tickets",
                "expenses",
                "inventory_items",
                "inventory_import_batches",
                "calendar_events",
                "travel_records",
                "reports",
                "communication_logs",
                "message_templates",
                "connectors",
                "chat_runs",
            ]:
                conn.execute(f"DELETE FROM {table}")

    def create_chat_run(self, command: str) -> int:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_runs (command, status, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (command, "running", None, now, now),
            )
            return int(cursor.lastrowid)

    def update_chat_run(self, run_id: int, status: str, summary: str) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE chat_runs
                SET status = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, summary, now, run_id),
            )
        return self.get_chat_run(run_id)

    def get_chat_run(self, run_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM chat_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else {}

    def seed_demo_users(self) -> None:
        demo_users = [
            {
                "email": "admin@company.com",
                "password": "admin123",
                "role": "admin",
                "name": "Admin User",
            },
            {
                "email": "finance@company.com",
                "password": "finance123",
                "role": "finance_manager",
                "name": "Finance Manager",
            },
            {
                "email": "it@company.com",
                "password": "it123",
                "role": "it_manager",
                "name": "IT Manager",
            },
            {
                "email": "employee@company.com",
                "password": "employee123",
                "role": "employee",
                "name": "Employee User",
            },
        ]
        for user in demo_users:
            existing = self.get_user_by_email(user["email"])
            if existing:
                self.update_user(
                    existing["id"],
                    password=user["password"],
                    name=user["name"],
                    role=user["role"],
                    enabled=True,
                    is_demo=True,
                )
            else:
                self.add_user({**user, "is_demo": True})
        legacy_operation = self.get_user_by_email("operation@company.com")
        if legacy_operation:
            self.update_user(
                legacy_operation["id"],
                role="employee",
                enabled=False,
            )

    def seed_message_templates(self) -> None:
        self.ensure_connector_schema()
        templates = [
            ("Vendor billing reminder", "both", "Vendor billing reminder", "Hello {name}, this is a reminder about the pending vendor billing item.", "vendors"),
            ("Vendor follow-up", "both", "Vendor follow-up", "Hello {name}, following up on our recent vendor discussion.", "vendors"),
            ("Expense approval", "both", "Expense approved", "Your expense request has been approved.", "expenses"),
            ("Expense rejection", "both", "Expense rejected", "Your expense request was rejected. Please review the comments.", "expenses"),
            ("Missing receipt reminder", "both", "Missing receipt reminder", "Please upload the missing receipt for your expense.", "expenses"),
            ("Ticket created", "both", "Ticket created", "Your ticket has been created and assigned to the relevant team.", "tickets"),
            ("Ticket resolved", "both", "Ticket resolved", "Your ticket has been resolved.", "tickets"),
            ("Report shared", "email", "Report shared", "A report has been shared with you from Agent Concierge.", "reports"),
            ("Travel approval", "both", "Travel approval update", "Your travel request has an approval update.", "travel"),
            ("General message", "both", "Agent Concierge message", "Hello {name}, sharing an update from Agent Concierge.", "general"),
        ]
        now = utc_now()
        with self.db.connection() as conn:
            for name, channel, subject, body, module in templates:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO message_templates (
                        name, channel, subject, body, module, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, channel, subject, body, module, now, now),
                )

    def seed_demo_tasks(self) -> None:
        if self.list_tasks():
            return

        def user(email: str) -> dict:
            found = self.get_user_by_email(email)
            if not found:
                raise ValueError(f"Demo user missing for task seed: {email}")
            return found

        admin = user("admin@company.com")
        it_manager = user("it@company.com")
        finance = user("finance@company.com")
        employee = user("employee@company.com")
        demo_tasks = [
            {
                "title": "Prepare vendor onboarding checklist",
                "description": "Create the checklist for new vendor KYC, billing setup, and contact verification.",
                "category": "Vendor",
                "department": "Admin",
                "assigned_to": admin["name"],
                "assigned_role": "admin",
                "priority": "High",
                "status": "Open",
                "due_date": "2026-05-10",
                "created_by": admin,
                "notes": "Coordinate with Finance before vendor activation.",
            },
            {
                "title": "Review printer inventory levels",
                "description": "Check printer cartridge counts and update low-stock records in Inventory.",
                "category": "Inventory",
                "department": "IT",
                "assigned_to": it_manager["name"],
                "assigned_role": "it_manager",
                "priority": "Medium",
                "status": "In Progress",
                "due_date": "2026-05-09",
                "created_by": admin,
                "notes": "",
            },
            {
                "title": "Validate invoice exception report",
                "description": "Review finance report exceptions and confirm whether approval is required.",
                "category": "Finance",
                "department": "Finance",
                "assigned_to": finance["name"],
                "assigned_role": "finance_manager",
                "priority": "Critical",
                "status": "Waiting Approval",
                "due_date": "2026-05-08",
                "created_by": finance,
                "notes": "Use the latest uploaded finance report.",
            },
            {
                "title": "Submit travel support details",
                "description": "Send travel dates and destination details for the upcoming client visit.",
                "category": "Travel",
                "department": "Operations",
                "assigned_to": employee["name"],
                "assigned_role": "employee",
                "priority": "Low",
                "status": "Open",
                "due_date": "2026-05-12",
                "created_by": admin,
                "notes": "",
            },
            {
                "title": "Publish monthly report summary",
                "description": "Upload the final monthly admin summary to Reports after review.",
                "category": "Report",
                "department": "Admin",
                "assigned_to": admin["name"],
                "assigned_role": "admin",
                "priority": "Medium",
                "status": "Completed",
                "due_date": "2026-05-06",
                "created_by": admin,
                "notes": "Completed demo task.",
            },
        ]
        for task in demo_tasks:
            creator = task.pop("created_by")
            self.add_task(
                {
                    **task,
                    "owner_name": task["assigned_to"],
                    "owner_email": creator["email"],
                    "source": "demo_seed",
                    "created_by_user_id": creator["id"],
                    "created_by_name": creator["name"],
                    "created_by_email": creator["email"],
                    "created_by_role": creator["role"],
                }
            )

    def seed_demo_tickets(self) -> None:
        if self.list_tickets():
            return

        def user(email: str) -> dict:
            found = self.get_user_by_email(email)
            if not found:
                raise ValueError(f"Demo user missing for ticket seed: {email}")
            return found

        demo_tickets = [
            {
                "ticket_id": "IT-1001",
                "ticket_type": "IT",
                "title": "Laptop password reset",
                "description": "Employee is locked out of the laptop after repeated password attempts.",
                "category": "Password",
                "priority": "High",
                "status": "Open",
                "requester": user("employee@company.com"),
                "assigned_role": "it_manager",
                "assigned_team": "IT Service Desk",
                "due_date": "2026-05-08",
                "approval_required": True,
            },
            {
                "ticket_id": "IT-1002",
                "ticket_type": "IT",
                "title": "New software access request",
                "description": "Request access to analytics and reporting software for monthly operations reporting.",
                "category": "Software Access",
                "priority": "Medium",
                "status": "Waiting Approval",
                "requester": user("employee@company.com"),
                "assigned_role": "it_manager",
                "assigned_team": "IT Service Desk",
                "due_date": "2026-05-10",
                "approval_required": True,
            },
            {
                "ticket_id": "IT-1003",
                "ticket_type": "IT",
                "title": "Printer not working",
                "description": "Finance floor printer is not accepting print jobs from shared laptops.",
                "category": "Printer",
                "priority": "Medium",
                "status": "In Progress",
                "requester": user("finance@company.com"),
                "assigned_role": "it_manager",
                "assigned_team": "IT Service Desk",
                "due_date": "2026-05-09",
                "approval_required": False,
            },
            {
                "ticket_id": "IT-1004",
                "ticket_type": "IT",
                "title": "Device replacement request",
                "description": "Replacement needed for a damaged operations tablet used at reception.",
                "category": "Device",
                "priority": "Critical",
                "status": "Waiting Approval",
                "requester": user("employee@company.com"),
                "assigned_role": "it_manager",
                "assigned_team": "IT Service Desk",
                "due_date": "2026-05-08",
                "approval_required": True,
            },
            {
                "ticket_id": "ADM-1001",
                "ticket_type": "Admin",
                "title": "Meeting room booking",
                "description": "Book the large meeting room for the weekly vendor review.",
                "category": "Meeting Support",
                "priority": "Low",
                "status": "Open",
                "requester": user("employee@company.com"),
                "assigned_role": "admin",
                "assigned_team": "Admin",
                "due_date": "2026-05-09",
                "approval_required": False,
            },
            {
                "ticket_id": "ADM-1002",
                "ticket_type": "Admin",
                "title": "Vendor invoice follow-up",
                "description": "Follow up on pending vendor invoice clarification before monthly close.",
                "category": "Finance",
                "priority": "High",
                "status": "Waiting Approval",
                "requester": user("finance@company.com"),
                "assigned_role": "finance_manager",
                "assigned_team": "Finance",
                "due_date": "2026-05-11",
                "approval_required": True,
            },
            {
                "ticket_id": "ADM-1003",
                "ticket_type": "Admin",
                "title": "Office supply request",
                "description": "Replenish printer paper, markers, and visitor badges for the front desk.",
                "category": "Office Supplies",
                "priority": "Medium",
                "status": "In Progress",
                "requester": user("it@company.com"),
                "assigned_role": "admin",
                "assigned_team": "Admin",
                "due_date": "2026-05-12",
                "approval_required": False,
            },
            {
                "ticket_id": "ADM-1004",
                "ticket_type": "Admin",
                "title": "Travel booking support",
                "description": "Coordinate travel booking support for the Delhi client visit.",
                "category": "Travel",
                "priority": "High",
                "status": "Waiting Approval",
                "requester": user("employee@company.com"),
                "assigned_role": "admin",
                "assigned_team": "Admin",
                "due_date": "2026-05-13",
                "approval_required": True,
            },
        ]
        for ticket in demo_tickets:
            requester = ticket.pop("requester")
            self.add_ticket(
                {
                    **ticket,
                    "requester_user_id": requester["id"],
                    "requester_name": requester["name"],
                    "requester_email": requester["email"],
                    "requester_role": requester["role"],
                }
            )

    def seed_demo_expenses(self) -> None:
        if self.list_expenses():
            return

        def user(email: str) -> dict:
            found = self.get_user_by_email(email)
            if not found:
                raise ValueError(f"Demo user missing for expense seed: {email}")
            return found

        employee = user("employee@company.com")
        finance = user("finance@company.com")
        it_manager = user("it@company.com")
        admin = user("admin@company.com")
        demo_expenses = [
            {
                "employee": employee,
                "department": "Operations",
                "category": "Travel",
                "vendor_merchant": "Indigo Airlines",
                "amount": 12450,
                "currency": "INR",
                "expense_date": "2026-05-03",
                "payment_mode": "Corporate Card",
                "receipt_status": "Attached",
                "receipt_attachment_name": "indigo-del-blr.pdf",
                "notes": "Client visit airfare.",
                "status": "Pending Approval",
                "approval_required": True,
                "approved_by": "",
            },
            {
                "employee": employee,
                "department": "Operations",
                "category": "Food",
                "vendor_merchant": "Team Lunch Cafe",
                "amount": 1850,
                "currency": "INR",
                "expense_date": "2026-05-05",
                "payment_mode": "UPI",
                "receipt_status": "Missing",
                "receipt_attachment_name": "",
                "notes": "Working lunch during vendor review prep.",
                "status": "Needs Info",
                "approval_required": True,
                "approved_by": "",
            },
            {
                "employee": finance,
                "department": "Finance",
                "category": "Vendor Payment",
                "vendor_merchant": "Acme Facilities",
                "amount": 47200,
                "currency": "INR",
                "expense_date": "2026-05-01",
                "payment_mode": "Bank Transfer",
                "receipt_status": "Attached",
                "receipt_attachment_name": "acme-invoice-4521.pdf",
                "notes": "Monthly facilities support invoice.",
                "status": "Approved",
                "approval_required": True,
                "approved_by": admin["name"],
            },
            {
                "employee": it_manager,
                "department": "IT",
                "category": "Software",
                "vendor_merchant": "Figma",
                "amount": 6800,
                "currency": "INR",
                "expense_date": "2026-05-02",
                "payment_mode": "Corporate Card",
                "receipt_status": "Attached",
                "receipt_attachment_name": "figma-license.pdf",
                "notes": "Design tool subscription renewal.",
                "status": "Paid",
                "approval_required": False,
                "approved_by": finance["name"],
            },
            {
                "employee": employee,
                "department": "Admin",
                "category": "Office Supplies",
                "vendor_merchant": "Stationery Central",
                "amount": 3200,
                "currency": "INR",
                "expense_date": "2026-04-30",
                "payment_mode": "Cash",
                "receipt_status": "Attached",
                "receipt_attachment_name": "stationery-april.pdf",
                "notes": "Printer paper and visitor badges.",
                "status": "Reimbursed",
                "approval_required": False,
                "approved_by": finance["name"],
            },
        ]
        for expense in demo_expenses:
            employee_user = expense.pop("employee")
            self.add_expense(
                {
                    **expense,
                    "employee_user_id": employee_user["id"],
                    "employee_name": employee_user["name"],
                    "employee_email": employee_user["email"],
                    "employee_role": employee_user["role"],
                }
            )

    def seed_demo_inventory(self) -> None:
        if self.list_inventory_items():
            return
        demo_items = [
            {
                "item_id": "INV-IT-1001",
                "item_name": "MacBook Pro 14",
                "category": "IT Equipment",
                "subcategory": "Laptop",
                "brand": "Apple",
                "model": "MacBook Pro 14 M3",
                "serial_number": "MBP14-AC-001",
                "quantity": 1,
                "unit": "pcs",
                "condition": "Good",
                "location": "IT Store",
                "assigned_to": "Admin User",
                "department": "IT",
                "purchase_date": "2025-09-12",
                "warranty_end_date": "2028-09-11",
                "vendor": "Rohit Tech Supplies",
                "minimum_stock_level": 1,
                "employee_name": "Admin User",
                "serial_no": "MBP14-AC-001",
                "model_no": "MacBook Pro 14 M3",
                "ram": "32 GB",
                "disk": "1 TB SSD",
                "status": "In Use",
                "notes": "Primary admin workstation.",
            },
            {
                "item_id": "INV-IT-1002",
                "item_name": "Wireless Keyboard",
                "category": "IT Equipment",
                "subcategory": "Peripheral",
                "brand": "Logitech",
                "model": "MX Keys",
                "serial_number": "LOGI-MX-044",
                "quantity": 4,
                "unit": "pcs",
                "condition": "New",
                "location": "IT Store",
                "assigned_to": "",
                "department": "IT",
                "purchase_date": "2026-01-18",
                "warranty_end_date": "2027-01-17",
                "vendor": "Office Digital",
                "minimum_stock_level": 2,
                "employee_name": "",
                "serial_no": "LOGI-MX-044",
                "model_no": "MX Keys",
                "ram": "—",
                "disk": "—",
                "status": "Extra",
                "notes": "",
            },
            {
                "item_id": "INV-ST-1001",
                "item_name": "A4 Copier Paper",
                "category": "Stationery Equipment",
                "subcategory": "Paper",
                "brand": "JK Copier",
                "model": "75 GSM",
                "serial_number": "",
                "quantity": 8,
                "unit": "ream",
                "condition": "New",
                "location": "Admin Store",
                "assigned_to": "",
                "department": "Admin",
                "purchase_date": "2026-04-20",
                "warranty_end_date": "",
                "vendor": "Stationery Central",
                "minimum_stock_level": 10,
                "employee_name": "",
                "serial_no": "",
                "model_no": "75 GSM",
                "ram": "—",
                "disk": "—",
                "status": "Extra",
                "notes": "Below minimum level for monthly usage.",
            },
            {
                "item_id": "INV-ON-1001",
                "item_name": "Welcome Kit",
                "category": "Onboarding Equipment",
                "subcategory": "New Hire Kit",
                "brand": "Agent Concierge",
                "model": "Standard",
                "serial_number": "",
                "quantity": 12,
                "unit": "kit",
                "condition": "New",
                "location": "HR Cabinet",
                "assigned_to": "",
                "department": "HR",
                "purchase_date": "2026-03-03",
                "warranty_end_date": "",
                "vendor": "Print & Pack Co",
                "minimum_stock_level": 5,
                "employee_name": "",
                "serial_no": "",
                "model_no": "Standard",
                "ram": "—",
                "disk": "—",
                "status": "Extra",
                "notes": "Includes ID lanyard, notebook, and welcome card.",
            },
        ]
        for item in demo_items:
            self.add_inventory_item(item)

    def seed_demo_travel(self) -> None:
        if self.list_travel_records() or self.list_calendar_events():
            return

        demo_travel = [
            {
                "travel_id": "TRV-1001",
                "employee_name": "Admin User",
                "employee_email": "admin@company.com",
                "department": "Admin",
                "destination_from": "Pune",
                "destination_to": "Delhi",
                "travel_start_date": "2026-05-12",
                "travel_end_date": "2026-05-14",
                "purpose": "Client facility review and vendor coordination",
                "travel_mode": "Flight",
                "estimated_budget": 42000,
                "actual_spend": 38500,
                "number_of_trips": 1,
                "approval_status": "Approved",
                "policy_status": "Within Policy",
                "booking_status": "Booked",
                "notes": "Internal mock record ready for future Google Calendar sync.",
            },
            {
                "travel_id": "TRV-1002",
                "employee_name": "Finance Manager",
                "employee_email": "finance@company.com",
                "department": "Finance",
                "destination_from": "Pune",
                "destination_to": "Mumbai",
                "travel_start_date": "2026-05-08",
                "travel_end_date": "2026-05-08",
                "purpose": "Invoice audit and payment reconciliation",
                "travel_mode": "Train",
                "estimated_budget": 8500,
                "actual_spend": 9100,
                "number_of_trips": 1,
                "approval_status": "Pending Approval",
                "policy_status": "Over Budget",
                "booking_status": "Submitted",
                "notes": "Fare variance needs finance approval.",
            },
            {
                "travel_id": "TRV-1003",
                "employee_name": "Employee User",
                "employee_email": "employee@company.com",
                "department": "Operations",
                "destination_from": "Pune",
                "destination_to": "Bengaluru",
                "travel_start_date": "2026-04-20",
                "travel_end_date": "2026-04-22",
                "purpose": "Operations onboarding support",
                "travel_mode": "Mixed",
                "estimated_budget": 26000,
                "actual_spend": 24800,
                "number_of_trips": 1,
                "approval_status": "Approved",
                "policy_status": "Within Policy",
                "booking_status": "Completed",
                "notes": "Completed mock travel history.",
            },
            {
                "travel_id": "TRV-1004",
                "employee_name": "Admin User",
                "employee_email": "admin@company.com",
                "department": "Admin",
                "destination_from": "Pune",
                "destination_to": "Hyderabad",
                "travel_start_date": "2026-06-02",
                "travel_end_date": "2026-06-04",
                "purpose": "Vendor site inspection",
                "travel_mode": "Flight",
                "estimated_budget": 36000,
                "actual_spend": 0,
                "number_of_trips": 1,
                "approval_status": "Submitted",
                "policy_status": "Needs Review",
                "booking_status": "Draft",
                "notes": "Awaiting approval before booking.",
            },
        ]
        for record in demo_travel:
            self.add_travel_record(
                {
                    **record,
                    "google_calendar_event_id": "",
                    "google_sync_status": "Not Synced",
                    "google_last_synced_at": "",
                }
            )

        demo_events = [
            {
                "event_id": "CAL-1001",
                "title": "Delhi client facility review",
                "event_type": "Travel",
                "start_datetime": "2026-05-12T09:00:00",
                "end_datetime": "2026-05-12T18:00:00",
                "location": "Delhi",
                "attendees": "Admin User, Client Ops Lead",
                "related_travel_id": "TRV-1001",
                "reminder": "1 day before",
                "notes": "Placeholder calendar event for future Google sync.",
                "status": "Scheduled",
                "google_calendar_event_id": "",
                "google_sync_status": "Not Synced",
                "google_last_synced_at": "",
            },
            {
                "event_id": "CAL-1002",
                "title": "Mumbai invoice audit",
                "event_type": "Meeting",
                "start_datetime": "2026-05-08T11:00:00",
                "end_datetime": "2026-05-08T13:00:00",
                "location": "Mumbai Finance Office",
                "attendees": "Finance Manager, Vendor Billing Team",
                "related_travel_id": "TRV-1002",
                "reminder": "2 hours before",
                "notes": "Internal calendar event only.",
                "status": "Scheduled",
                "google_calendar_event_id": "",
                "google_sync_status": "Not Synced",
                "google_last_synced_at": "",
            },
            {
                "event_id": "CAL-1003",
                "title": "Vendor site inspection planning",
                "event_type": "Reminder",
                "start_datetime": "2026-05-29T15:00:00",
                "end_datetime": "2026-05-29T15:30:00",
                "location": "Agent Concierge HQ",
                "attendees": "Admin User",
                "related_travel_id": "TRV-1004",
                "reminder": "Same day",
                "notes": "Plan Hyderabad visit details.",
                "status": "Tentative",
                "google_calendar_event_id": "",
                "google_sync_status": "Not Synced",
                "google_last_synced_at": "",
            },
        ]
        for event in demo_events:
            self.add_calendar_event(event)

    def add_user(self, user: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password, name, role, enabled, is_demo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["email"].lower(),
                    user["password"],
                    user["name"],
                    user["role"],
                    1 if user.get("enabled", True) else 0,
                    1 if user.get("is_demo", False) else 0,
                    now,
                    now,
                ),
            )
            user_id = int(cursor.lastrowid)
        return self.get_user(user_id)

    def update_user(self, user_id: int, **updates: Any) -> dict:
        allowed = {"name", "email", "role", "enabled", "password", "is_demo"}
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_user(user_id)
        values = [1 if key == "enabled" and updates[key] else 0 if key == "enabled" else updates[key] for key in fields]
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values.extend([utc_now(), user_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE users SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_user(user_id)

    def get_user(self, user_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._user_from_row(row) if row else {}

    def get_user_by_email(self, email: str) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return self._user_from_row(row) if row else {}

    def list_users(self) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at ASC, id ASC").fetchall()
        return [self._user_from_row(row) for row in rows]

    def delete_user(self, user_id: int) -> dict:
        user = self.get_user(user_id)
        if not user:
            return {}
        with self.db.connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return user

    def add_session(self, *, token: str, user_id: int) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now),
            )
        return self.get_session(token)

    def get_session(self, token: str) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else {}

    def delete_session(self, token: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def add_agent_plan(self, *, run_id: int, planner_mode: str, plan: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_plans (
                    run_id, planner_mode, task_type, automation_level,
                    approval_required, approval_reason, risk_level, plan_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    planner_mode,
                    plan["task_type"],
                    plan["automation_level"],
                    1 if plan["approval_required"] else 0,
                    plan.get("approval_reason") or None,
                    plan["risk_level"],
                    _json(plan),
                    now,
                ),
            )
            plan_id = int(cursor.lastrowid)
        return self.get_agent_plan(plan_id)

    def get_agent_plan(self, plan_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM agent_plans WHERE id = ?", (plan_id,)).fetchone()
        return self._agent_plan_from_row(row) if row else {}

    def list_agent_plans(self, limit: int = 5) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_plans ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._agent_plan_from_row(row) for row in rows]

    def add_meeting(self, meeting: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO meetings (
                    title, vendor_id, vendor_name, scheduled_for, status,
                    agenda_json, attendees_json, files_json, reminder_message,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting["title"],
                    meeting["vendor_id"],
                    meeting["vendor_name"],
                    meeting["scheduled_for"],
                    meeting.get("status", "scheduled"),
                    _json(meeting.get("agenda", [])),
                    _json(meeting.get("attendees", [])),
                    _json(meeting.get("files", [])),
                    meeting.get("reminder_message"),
                    now,
                    now,
                ),
            )
            meeting_id = int(cursor.lastrowid)
        return self.get_meeting(meeting_id)

    def update_meeting(self, meeting_id: int, **updates: Any) -> dict:
        allowed = {
            "status",
            "agenda_json",
            "attendees_json",
            "files_json",
            "reminder_message",
        }
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_meeting(meeting_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = [updates[field] for field in fields]
        values.extend([utc_now(), meeting_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE meetings SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_meeting(meeting_id)

    def get_meeting(self, meeting_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        return self._meeting_from_row(row) if row else {}

    def list_meetings(self, limit: int = 10) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM meetings ORDER BY scheduled_for DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._meeting_from_row(row) for row in rows]

    def add_meeting_notes(self, payload: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO meeting_notes (
                    meeting_id, transcript, summary, decisions_json,
                    action_items_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["meeting_id"],
                    payload["transcript"],
                    payload["summary"],
                    _json(payload.get("decisions", [])),
                    _json(payload.get("action_items", [])),
                    now,
                ),
            )
            note_id = int(cursor.lastrowid)
        return self.get_meeting_note(note_id)

    def get_meeting_note(self, note_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM meeting_notes WHERE id = ?", (note_id,)).fetchone()
        return self._note_from_row(row) if row else {}

    def list_notes(self, limit: int = 5) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM meeting_notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._note_from_row(row) for row in rows]

    def _normalize_task_status(self, status: str | None) -> str:
        normalized = str(status or "Open").strip().lower().replace("_", " ")
        return {
            "open": "Open",
            "in progress": "In Progress",
            "waiting approval": "Waiting Approval",
            "completed": "Completed",
            "complete": "Completed",
            "done": "Completed",
            "cancelled": "Cancelled",
            "canceled": "Cancelled",
        }.get(normalized, status or "Open")

    def add_task(self, task: dict) -> dict:
        self.ensure_task_schema()
        now = utc_now()
        task_id = task.get("task_id") or self._next_task_id()
        owner_name = task.get("owner_name") or task.get("assigned_to") or task.get("created_by_name") or "Admin Team"
        owner_email = task.get("owner_email") or task.get("created_by_email") or ""
        source = task.get("source", "manual")
        category = task.get("category") or ("Vendor" if source == "meeting_action_item" else "Admin")
        assigned_to = task.get("assigned_to") or owner_name
        assigned_email = task.get("assigned_email") or owner_email
        assigned_role = _normalize_assigned_role(task.get("assigned_role", "admin"))
        status = self._normalize_task_status(task.get("status", "Open"))
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, category, department,
                    assigned_to, assigned_user_id, assigned_email, assigned_role,
                    priority, owner_name, owner_email,
                    due_date, status, source, meeting_id, created_by_user_id,
                    created_by_name, created_by_email, created_by_role, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task["title"],
                    task.get("description", task["title"]),
                    category,
                    task.get("department", "Admin"),
                    assigned_to,
                    task.get("assigned_user_id"),
                    assigned_email,
                    assigned_role,
                    task.get("priority", "Medium"),
                    owner_name,
                    owner_email,
                    str(task["due_date"]) if task.get("due_date") else "",
                    status,
                    source,
                    task.get("meeting_id"),
                    task.get("created_by_user_id"),
                    task.get("created_by_name", "Agent Concierge"),
                    task.get("created_by_email", "system@agent.local"),
                    _normalize_role_value(task.get("created_by_role", "admin")),
                    task.get("notes", ""),
                    now,
                    now,
                ),
            )
            task_id = int(cursor.lastrowid)
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> dict:
        self.ensure_task_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_from_row(row) if row else {}

    def list_tasks(self, status: str | None = None) -> list[dict]:
        self.ensure_task_schema()
        if status:
            query = "SELECT * FROM tasks WHERE status = ? ORDER BY due_date ASC"
            params: tuple[Any, ...] = (self._normalize_task_status(status),)
        else:
            query = "SELECT * FROM tasks ORDER BY due_date ASC, created_at DESC, id DESC"
            params = ()
        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._task_from_row(row) for row in rows]

    def update_task(self, task_id: int, **updates: Any) -> dict:
        self.ensure_task_schema()
        allowed = {
            "title",
            "description",
            "category",
            "department",
            "assigned_to",
            "assigned_user_id",
            "assigned_email",
            "assigned_role",
            "priority",
            "status",
            "due_date",
            "notes",
        }
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_task(task_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for key in fields:
            if key == "status":
                values.append(self._normalize_task_status(updates[key]))
            elif key == "assigned_role":
                values.append(_normalize_assigned_role(updates[key]))
            elif key == "due_date":
                values.append(str(updates[key]) if updates.get(key) else "")
            else:
                values.append(updates[key])
        values.extend([utc_now(), task_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE tasks SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
            if "assigned_to" in updates:
                conn.execute(
                    "UPDATE tasks SET owner_name = ?, owner_email = COALESCE(NULLIF(?, ''), owner_email) WHERE id = ?",
                    (updates["assigned_to"], updates.get("assigned_email", ""), task_id),
                )
        return self.get_task(task_id)

    def update_task_status(self, task_id: int, status: str) -> dict:
        return self.update_task(task_id, status=status)

    def delete_task(self, task_id: int) -> dict:
        task = self.get_task(task_id)
        if not task:
            return {}
        with self.db.connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return task

    def add_approval(self, approval: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO approvals (
                    approval_type, status, risk_reason, recipient_name,
                    recipient_email, subject, body, original_body,
                    related_meeting_id, created_at, updated_at, sent_at,
                    cancelled_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval["approval_type"],
                    approval.get("status", "pending"),
                    approval["risk_reason"],
                    approval["recipient_name"],
                    approval["recipient_email"],
                    approval["subject"],
                    approval["body"],
                    approval.get("original_body", approval["body"]),
                    approval.get("related_meeting_id"),
                    now,
                    now,
                    approval.get("sent_at"),
                    approval.get("cancelled_reason"),
                ),
            )
            approval_id = int(cursor.lastrowid)
        return self.get_approval(approval_id)

    def update_approval(self, approval_id: int, **updates: Any) -> dict:
        allowed = {
            "status",
            "subject",
            "body",
            "sent_at",
            "cancelled_reason",
        }
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_approval(approval_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = [updates[field] for field in fields]
        values.extend([utc_now(), approval_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE approvals SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        return self._approval_from_row(row) if row else {}

    def list_approvals(self, status: str | None = None) -> list[dict]:
        if status:
            query = "SELECT * FROM approvals WHERE status = ? ORDER BY created_at DESC"
            params: tuple[Any, ...] = (status,)
        else:
            query = "SELECT * FROM approvals ORDER BY created_at DESC"
            params = ()
        with self.db.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def add_routed_request(self, *, message: str, route: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO routed_requests (
                    message, task_type, priority, risk_level, status,
                    requester_user_id, assigned_role, required_approval_roles_json,
                    approval_required, approval_reason, approval_type, created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message,
                    route["task_type"],
                    route["priority"],
                    route["risk_level"],
                    route["status"],
                    route.get("requester_user_id"),
                    route["assigned_role"],
                    _json(route.get("required_approval_roles", [])),
                    1 if route["approval_required"] else 0,
                    route.get("approval_reason") or None,
                    route.get("approval_type"),
                    now,
                    now,
                ),
            )
            route_id = int(cursor.lastrowid)
        return self.get_routed_request(route_id)

    def get_routed_request(self, route_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM routed_requests WHERE id = ?", (route_id,)).fetchone()
        return self._routed_request_from_row(row) if row else {}

    def list_routed_requests(self, limit: int = 50) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM routed_requests ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._routed_request_from_row(row) for row in rows]

    def add_vendor(self, vendor: dict) -> dict:
        self.ensure_vendor_schema()
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO vendors (
                    vendor_name, contact_person, email, contact_details,
                    office_address, service_provided, start_date, end_date,
                    billing_amount, billing_cycle, status, created_by_user_id, created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vendor["vendor_name"],
                    vendor["contact_person"],
                    vendor["email"].lower(),
                    vendor["contact_details"],
                    vendor["office_address"],
                    vendor["service_provided"],
                    str(vendor["start_date"]),
                    str(vendor["end_date"]) if vendor.get("end_date") else "",
                    int(vendor["billing_amount"]),
                    vendor["billing_cycle"],
                    vendor.get("status", "active"),
                    vendor.get("created_by_user_id"),
                    now,
                    now,
                ),
            )
            vendor_id = int(cursor.lastrowid)
        return self.get_vendor(vendor_id)

    def get_vendor(self, vendor_id: int) -> dict:
        self.ensure_vendor_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        return self._vendor_from_row(row) if row else {}

    def update_vendor(self, vendor_id: int, vendor: dict) -> dict:
        self.ensure_vendor_schema()
        allowed = {
            "vendor_name",
            "contact_person",
            "email",
            "contact_details",
            "office_address",
            "service_provided",
            "start_date",
            "end_date",
            "billing_amount",
            "billing_cycle",
            "status",
        }
        fields = [key for key in vendor if key in allowed]
        if not fields:
            return self.get_vendor(vendor_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for field in fields:
            if field == "email":
                values.append(str(vendor[field]).lower())
            elif field in {"start_date", "end_date"}:
                values.append(str(vendor[field]) if vendor.get(field) else "")
            elif field == "billing_amount":
                values.append(int(vendor[field]))
            else:
                values.append(vendor[field])
        values.extend([utc_now(), vendor_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE vendors SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_vendor(vendor_id)

    def list_vendors(self) -> list[dict]:
        self.ensure_vendor_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM vendors ORDER BY created_at DESC, id DESC",
            ).fetchall()
        return [self._vendor_from_row(row) for row in rows]

    def add_expense(self, expense: dict) -> dict:
        self.ensure_expense_schema()
        now = utc_now()
        expense_id = expense.get("expense_id") or self._next_expense_id()
        if self.get_expense_by_expense_id(expense_id):
            raise ValueError("Expense ID already exists")
        policy_exceptions = expense.get("policy_exceptions") or self._expense_policy_exceptions(expense)
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses (
                    expense_id, employee_user_id, employee_name, employee_email,
                    employee_role, department, category, vendor_merchant, amount,
                    currency, expense_date, payment_mode, receipt_status,
                    receipt_attachment_name, notes, status, approval_required,
                    approved_by, policy_exceptions_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    expense_id,
                    expense.get("employee_user_id"),
                    expense["employee_name"],
                    expense["employee_email"].lower(),
                    expense.get("employee_role", ""),
                    expense["department"],
                    expense["category"],
                    expense["vendor_merchant"],
                    float(expense["amount"]),
                    expense.get("currency", "INR"),
                    str(expense["expense_date"]) if expense.get("expense_date") else "",
                    expense["payment_mode"],
                    expense["receipt_status"],
                    expense.get("receipt_attachment_name", ""),
                    expense.get("notes", ""),
                    expense.get("status", "Draft"),
                    1 if expense.get("approval_required") else 0,
                    expense.get("approved_by", ""),
                    _json(policy_exceptions),
                    now,
                    now,
                ),
            )
            expense_row_id = int(cursor.lastrowid)
        return self.get_expense(expense_row_id)

    def get_expense_by_expense_id(self, expense_id: str) -> dict:
        self.ensure_expense_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE expense_id = ?", (expense_id,)).fetchone()
        return self._expense_from_row(row) if row else {}

    def get_expense(self, expense_id: int) -> dict:
        self.ensure_expense_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return self._expense_from_row(row) if row else {}

    def list_expenses(self) -> list[dict]:
        self.ensure_expense_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM expenses ORDER BY created_at DESC, id DESC",
            ).fetchall()
        return [self._expense_from_row(row) for row in rows]

    def update_expense(self, expense_id: int, **updates: Any) -> dict:
        self.ensure_expense_schema()
        existing = self.get_expense(expense_id)
        if not existing:
            return {}
        allowed = {
            "employee_user_id",
            "employee_name",
            "employee_email",
            "employee_role",
            "department",
            "category",
            "vendor_merchant",
            "amount",
            "currency",
            "expense_date",
            "payment_mode",
            "receipt_status",
            "receipt_attachment_name",
            "notes",
            "status",
            "approval_required",
            "approved_by",
            "policy_exceptions",
        }
        fields = [key for key in updates if key in allowed]
        if not fields:
            return existing
        merged = {**existing, **updates}
        if "policy_exceptions" not in updates:
            updates["policy_exceptions"] = self._expense_policy_exceptions(merged)
            fields.append("policy_exceptions")
        column_map = {"policy_exceptions": "policy_exceptions_json"}
        assignments = ", ".join([f"{column_map.get(field, field)} = ?" for field in fields])
        values = []
        for field in fields:
            if field == "approval_required":
                values.append(1 if updates[field] else 0)
            elif field == "amount":
                values.append(float(updates[field]))
            elif field == "employee_email":
                values.append(str(updates[field]).lower())
            elif field == "expense_date":
                values.append(str(updates[field]) if updates.get(field) else "")
            elif field == "policy_exceptions":
                values.append(_json(updates[field]))
            else:
                values.append(updates[field])
        values.extend([utc_now(), expense_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE expenses SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_expense(expense_id)

    def update_expense_status(self, expense_id: int, status: str, approved_by: str = "") -> dict:
        updates: dict[str, Any] = {"status": status}
        if approved_by:
            updates["approved_by"] = approved_by
        return self.update_expense(expense_id, **updates)

    def _next_expense_id(self) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT expense_id FROM expenses WHERE expense_id LIKE 'EXP-%' ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if not row:
            return "EXP-1001"
        try:
            number = int(str(row["expense_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"EXP-{number}"

    def _expense_policy_exceptions(self, expense: dict) -> list[str]:
        exceptions: list[str] = []
        amount = float(expense.get("amount") or 0)
        category = str(expense.get("category") or "")
        notes = f"{expense.get('notes', '')} {expense.get('vendor_merchant', '')}".lower()
        receipt_status = str(expense.get("receipt_status") or "").lower()
        limits = {
            "Travel": 10000,
            "Hotel": 12000,
            "Food": 2500,
            "Local Conveyance": 3000,
            "Office Supplies": 5000,
            "Software": 7500,
            "Internet / Phone": 3000,
            "Vendor Payment": 25000,
            "Client Meeting": 6000,
            "Training": 10000,
            "Miscellaneous": 3000,
        }
        if amount > limits.get(category, 5000):
            exceptions.append("Amount over policy limit")
        if receipt_status in {"missing", "pending"}:
            exceptions.append("Missing receipt")
        if "duplicate" in notes:
            exceptions.append("Duplicate receipt")
        if "non-refundable" in notes or "non refundable" in notes:
            exceptions.append("Non-refundable ticket")
        if "wrong category" in notes:
            exceptions.append("Wrong category")
        if any(term in notes for term in ["weekend", "late night", "late-night"]):
            exceptions.append("Weekend/late-night expense")
        return exceptions

    def _normalize_inventory_item_payload(self, item: dict) -> dict:
        normalized = dict(item)
        employee_name = str(normalized.get("employee_name") or normalized.get("assigned_to") or "").strip()
        serial_no = str(normalized.get("serial_no") or normalized.get("serial_number") or "").strip()
        model_no = str(normalized.get("model_no") or normalized.get("model") or "").strip()
        normalized["employee_name"] = employee_name
        normalized["serial_no"] = serial_no
        normalized["model_no"] = model_no
        normalized["ram"] = str(normalized.get("ram", "") or "").strip()
        normalized["disk"] = str(normalized.get("disk", "") or "").strip()
        normalized["assigned_to"] = str(normalized.get("assigned_to") or employee_name).strip()
        normalized["serial_number"] = str(normalized.get("serial_number") or serial_no).strip()
        normalized["model"] = str(normalized.get("model") or model_no).strip()
        normalized["item_name"] = str(normalized.get("item_name") or employee_name or model_no or "Inventory Item").strip()
        normalized["category"] = str(normalized.get("category") or "IT Equipment").strip()
        normalized["subcategory"] = str(normalized.get("subcategory", "") or "").strip()
        normalized["brand"] = str(normalized.get("brand", "") or "").strip()
        normalized["quantity"] = int(normalized.get("quantity") or 1)
        normalized["unit"] = str(normalized.get("unit") or "unit").strip()
        normalized["condition"] = str(normalized.get("condition") or "Good").strip()
        normalized["location"] = str(normalized.get("location") or "").strip()
        normalized["department"] = str(normalized.get("department", "") or "").strip()
        normalized["vendor"] = str(normalized.get("vendor", "") or "").strip()
        normalized["minimum_stock_level"] = int(normalized.get("minimum_stock_level") or 0)
        normalized["status"] = str(normalized.get("status") or "In Use").strip()
        normalized["notes"] = str(normalized.get("notes", "") or "").strip()
        if not str(normalized.get("item_id", "") or "").strip():
            source = serial_no or f"{employee_name}-{model_no}" or "inventory-item"
            slug = "".join(char if char.isalnum() else "-" for char in source.upper()).strip("-")
            normalized["item_id"] = f"INV-{slug or int(datetime.now(timezone.utc).timestamp())}"
        else:
            normalized["item_id"] = str(normalized["item_id"]).strip()
        return normalized

    def add_inventory_item(self, item: dict) -> dict:
        self.ensure_inventory_schema()
        item = self._normalize_inventory_item_payload(item)
        if self.get_inventory_item_by_item_id(item["item_id"]):
            raise ValueError("Inventory item ID already exists")
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inventory_items (
                    item_id, item_name, category, subcategory, brand, model,
                    serial_number, quantity, unit, condition, location, assigned_to,
                    department, purchase_date, warranty_end_date, vendor,
                    minimum_stock_level, employee_name, serial_no, model_no, ram, disk,
                    status, notes, import_batch_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["item_id"],
                    item["item_name"],
                    item["category"],
                    item.get("subcategory", ""),
                    item.get("brand", ""),
                    item.get("model", ""),
                    item.get("serial_number", ""),
                    int(item["quantity"]),
                    item["unit"],
                    item["condition"],
                    item["location"],
                    item.get("assigned_to", ""),
                    item["department"],
                    str(item["purchase_date"]) if item.get("purchase_date") else "",
                    str(item["warranty_end_date"]) if item.get("warranty_end_date") else "",
                    item.get("vendor", ""),
                    int(item["minimum_stock_level"]),
                    item.get("employee_name", ""),
                    item.get("serial_no", ""),
                    item.get("model_no", ""),
                    item.get("ram", ""),
                    item.get("disk", ""),
                    item["status"],
                    item.get("notes", ""),
                    item.get("import_batch_id"),
                    now,
                    now,
                ),
            )
            inventory_id = int(cursor.lastrowid)
        return self.get_inventory_item(inventory_id)

    def get_inventory_item(self, inventory_id: int) -> dict:
        self.ensure_inventory_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM inventory_items WHERE id = ?", (inventory_id,)).fetchone()
        return self._inventory_item_from_row(row) if row else {}

    def get_inventory_item_by_item_id(self, item_id: str) -> dict:
        self.ensure_inventory_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM inventory_items WHERE item_id = ?", (item_id,)).fetchone()
        return self._inventory_item_from_row(row) if row else {}

    def list_inventory_items(self) -> list[dict]:
        self.ensure_inventory_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM inventory_items ORDER BY created_at DESC, id DESC",
            ).fetchall()
        return [self._inventory_item_from_row(row) for row in rows]

    def list_inventory_items_for_import(self, import_batch_id: int) -> list[dict]:
        self.ensure_inventory_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM inventory_items WHERE import_batch_id = ? ORDER BY created_at DESC, id DESC",
                (import_batch_id,),
            ).fetchall()
        return [self._inventory_item_from_row(row) for row in rows]

    def list_unbatched_inventory_items(self) -> list[dict]:
        self.ensure_inventory_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM inventory_items WHERE import_batch_id IS NULL ORDER BY created_at DESC, id DESC",
            ).fetchall()
        return [self._inventory_item_from_row(row) for row in rows]

    def update_inventory_item(self, inventory_id: int, item: dict) -> dict:
        self.ensure_inventory_schema()
        item = self._normalize_inventory_item_payload(item)
        existing_same_item_id = self.get_inventory_item_by_item_id(item["item_id"])
        if existing_same_item_id and existing_same_item_id["id"] != inventory_id:
            raise ValueError("Inventory item ID already exists")
        allowed = {
            "item_id",
            "item_name",
            "category",
            "subcategory",
            "brand",
            "model",
            "serial_number",
            "quantity",
            "unit",
            "condition",
            "location",
            "assigned_to",
            "department",
            "purchase_date",
            "warranty_end_date",
            "vendor",
            "minimum_stock_level",
            "employee_name",
            "serial_no",
            "model_no",
            "ram",
            "disk",
            "status",
            "notes",
        }
        fields = [key for key in item if key in allowed]
        if not fields:
            return self.get_inventory_item(inventory_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for field in fields:
            if field in {"quantity", "minimum_stock_level"}:
                values.append(int(item[field]))
            elif field in {"purchase_date", "warranty_end_date"}:
                values.append(str(item[field]) if item.get(field) else "")
            else:
                values.append(item[field])
        values.extend([utc_now(), inventory_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE inventory_items SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_inventory_item(inventory_id)

    def delete_inventory_item(self, inventory_id: int) -> dict:
        self.ensure_inventory_schema()
        item = self.get_inventory_item(inventory_id)
        if not item:
            return {}
        with self.db.connection() as conn:
            conn.execute("DELETE FROM inventory_items WHERE id = ?", (inventory_id,))
        return item

    def delete_inventory_items(self, inventory_ids: list[int]) -> list[dict]:
        self.ensure_inventory_schema()
        deleted = []
        for inventory_id in inventory_ids:
            item = self.delete_inventory_item(inventory_id)
            if item:
                deleted.append(item)
        return deleted

    def add_inventory_import_batch(self, batch: dict) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inventory_import_batches (
                    file_name, imported_by_user_id, imported_by_name, imported_by_email,
                    imported_at, total_rows, successful_rows, failed_rows, status,
                    notes, deleted_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch["file_name"],
                    batch.get("imported_by_user_id"),
                    batch.get("imported_by_name", ""),
                    batch.get("imported_by_email", ""),
                    now,
                    int(batch.get("total_rows", 0)),
                    int(batch.get("successful_rows", 0)),
                    int(batch.get("failed_rows", 0)),
                    batch.get("status", "Failed"),
                    batch.get("notes", ""),
                    batch.get("deleted_at"),
                    now,
                    now,
                ),
            )
            batch_id = int(cursor.lastrowid)
        return self.get_inventory_import_batch(batch_id)

    def update_inventory_import_batch(self, batch_id: int, **updates: Any) -> dict:
        allowed = {"total_rows", "successful_rows", "failed_rows", "status", "notes", "deleted_at"}
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_inventory_import_batch(batch_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = [int(updates[field]) if field in {"total_rows", "successful_rows", "failed_rows"} else updates[field] for field in fields]
        values.extend([utc_now(), batch_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE inventory_import_batches SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_inventory_import_batch(batch_id)

    def get_inventory_import_batch(self, batch_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM inventory_import_batches WHERE id = ?", (batch_id,)).fetchone()
        return self._inventory_import_batch_from_row(row) if row else {}

    def list_inventory_import_batches(self, include_legacy: bool = True) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM inventory_import_batches ORDER BY imported_at DESC, id DESC",
            ).fetchall()
        batches = [self._inventory_import_batch_from_row(row) for row in rows]
        if include_legacy:
            legacy_items = self.list_unbatched_inventory_items()
            if legacy_items:
                batches.append(
                    {
                        "id": "legacy-unbatched",
                        "file_name": "Legacy unbatched inventory",
                        "imported_by_user_id": None,
                        "imported_by_name": "Pre-batch data",
                        "imported_by_email": "",
                        "imported_at": "",
                        "total_rows": len(legacy_items),
                        "successful_rows": len(legacy_items),
                        "failed_rows": 0,
                        "status": "Legacy Unbatched",
                        "notes": "Inventory created before import batch tracking. This can include manual items.",
                        "deleted_at": "",
                        "created_at": "",
                        "updated_at": "",
                        "is_legacy_unbatched": True,
                    }
                )
        return batches

    def delete_inventory_import_batch_items(self, batch_id: int) -> list[dict]:
        items = self.list_inventory_items_for_import(batch_id)
        deleted = self.delete_inventory_items([item["id"] for item in items])
        self.update_inventory_import_batch(
            batch_id,
            status="Deleted",
            deleted_at=utc_now(),
            notes=f"Deleted {len(deleted)} inventory items from this import batch.",
        )
        return deleted

    def delete_unbatched_inventory_items(self) -> list[dict]:
        items = self.list_unbatched_inventory_items()
        return self.delete_inventory_items([item["id"] for item in items])

    def add_travel_record(self, record: dict) -> dict:
        self.ensure_travel_schema()
        now = utc_now()
        travel_id = record.get("travel_id") or self._next_travel_id()
        if self.get_travel_record_by_travel_id(travel_id):
            raise ValueError("Travel ID already exists")
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO travel_records (
                    travel_id, employee_name, employee_email, department,
                    destination_from, destination_to, travel_start_date,
                    travel_end_date, purpose, travel_mode, estimated_budget,
                    actual_spend, number_of_trips, approval_status, policy_status,
                    booking_status, notes, google_calendar_event_id,
                    google_sync_status, google_last_synced_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    travel_id,
                    record["employee_name"],
                    record["employee_email"].lower(),
                    record["department"],
                    record["destination_from"],
                    record["destination_to"],
                    str(record["travel_start_date"]),
                    str(record["travel_end_date"]),
                    record["purpose"],
                    record["travel_mode"],
                    float(record["estimated_budget"]),
                    float(record["actual_spend"]),
                    int(record["number_of_trips"]),
                    record.get("approval_status", "Draft"),
                    record.get("policy_status", "Within Policy"),
                    record.get("booking_status", "Draft"),
                    record.get("notes", ""),
                    record.get("google_calendar_event_id", ""),
                    record.get("google_sync_status", "Not Synced"),
                    str(record["google_last_synced_at"]) if record.get("google_last_synced_at") else "",
                    now,
                    now,
                ),
            )
            row_id = int(cursor.lastrowid)
        return self.get_travel_record(row_id)

    def get_travel_record(self, record_id: int) -> dict:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM travel_records WHERE id = ?", (record_id,)).fetchone()
        return self._travel_record_from_row(row) if row else {}

    def get_travel_record_by_travel_id(self, travel_id: str) -> dict:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM travel_records WHERE travel_id = ?", (travel_id,)).fetchone()
        return self._travel_record_from_row(row) if row else {}

    def list_travel_records(self) -> list[dict]:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM travel_records ORDER BY travel_start_date DESC, created_at DESC, id DESC",
            ).fetchall()
        return [self._travel_record_from_row(row) for row in rows]

    def update_travel_record(self, record_id: int, record: dict) -> dict:
        self.ensure_travel_schema()
        existing = self.get_travel_record(record_id)
        if not existing:
            return {}
        incoming_travel_id = record.get("travel_id") or existing["travel_id"]
        duplicate = self.get_travel_record_by_travel_id(incoming_travel_id)
        if duplicate and duplicate["id"] != record_id:
            raise ValueError("Travel ID already exists")
        allowed = {
            "travel_id",
            "employee_name",
            "employee_email",
            "department",
            "destination_from",
            "destination_to",
            "travel_start_date",
            "travel_end_date",
            "purpose",
            "travel_mode",
            "estimated_budget",
            "actual_spend",
            "number_of_trips",
            "approval_status",
            "policy_status",
            "booking_status",
            "notes",
            "google_calendar_event_id",
            "google_sync_status",
            "google_last_synced_at",
        }
        fields = [key for key in record if key in allowed]
        if "travel_id" not in fields:
            fields.append("travel_id")
            record["travel_id"] = incoming_travel_id
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for field in fields:
            if field in {"estimated_budget", "actual_spend"}:
                values.append(float(record[field]))
            elif field == "number_of_trips":
                values.append(int(record[field]))
            elif field == "employee_email":
                values.append(str(record[field]).lower())
            elif field in {"travel_start_date", "travel_end_date", "google_last_synced_at"}:
                values.append(str(record[field]) if record.get(field) else "")
            else:
                values.append(record[field])
        values.extend([utc_now(), record_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE travel_records SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_travel_record(record_id)

    def add_calendar_event(self, event: dict) -> dict:
        self.ensure_travel_schema()
        now = utc_now()
        event_id = event.get("event_id") or self._next_calendar_event_id()
        if self.get_calendar_event_by_event_id(event_id):
            raise ValueError("Calendar Event ID already exists")
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calendar_events (
                    event_id, title, event_type, start_datetime, end_datetime,
                    location, attendees, related_travel_id, reminder, notes, status,
                    google_calendar_event_id, google_sync_status,
                    google_last_synced_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event["title"],
                    event["event_type"],
                    str(event["start_datetime"]),
                    str(event["end_datetime"]),
                    event.get("location", ""),
                    event.get("attendees", ""),
                    event.get("related_travel_id", ""),
                    event.get("reminder", ""),
                    event.get("notes", ""),
                    event.get("status", "Scheduled"),
                    event.get("google_calendar_event_id", ""),
                    event.get("google_sync_status", "Not Synced"),
                    str(event["google_last_synced_at"]) if event.get("google_last_synced_at") else "",
                    now,
                    now,
                ),
            )
            row_id = int(cursor.lastrowid)
        return self.get_calendar_event(row_id)

    def get_calendar_event(self, event_row_id: int) -> dict:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_row_id,)).fetchone()
        return self._calendar_event_from_row(row) if row else {}

    def get_calendar_event_by_event_id(self, event_id: str) -> dict:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM calendar_events WHERE event_id = ?", (event_id,)).fetchone()
        return self._calendar_event_from_row(row) if row else {}

    def list_calendar_events(self) -> list[dict]:
        self.ensure_travel_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM calendar_events ORDER BY start_datetime ASC, created_at DESC, id DESC",
            ).fetchall()
        return [self._calendar_event_from_row(row) for row in rows]

    def update_calendar_event(self, event_row_id: int, event: dict) -> dict:
        self.ensure_travel_schema()
        existing = self.get_calendar_event(event_row_id)
        if not existing:
            return {}
        incoming_event_id = event.get("event_id") or existing["event_id"]
        duplicate = self.get_calendar_event_by_event_id(incoming_event_id)
        if duplicate and duplicate["id"] != event_row_id:
            raise ValueError("Calendar Event ID already exists")
        allowed = {
            "event_id",
            "title",
            "event_type",
            "start_datetime",
            "end_datetime",
            "location",
            "attendees",
            "related_travel_id",
            "reminder",
            "notes",
            "status",
            "google_calendar_event_id",
            "google_sync_status",
            "google_last_synced_at",
        }
        fields = [key for key in event if key in allowed]
        if "event_id" not in fields:
            fields.append("event_id")
            event["event_id"] = incoming_event_id
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for field in fields:
            if field in {"start_datetime", "end_datetime", "google_last_synced_at"}:
                values.append(str(event[field]) if event.get(field) else "")
            else:
                values.append(event[field])
        values.extend([utc_now(), event_row_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE calendar_events SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_calendar_event(event_row_id)

    def travel_summary(self) -> dict:
        records = self.list_travel_records()
        events = self.list_calendar_events()
        today = datetime.now(timezone.utc).date()

        def date_value(value: str):
            try:
                return datetime.fromisoformat(str(value)[:10]).date()
            except ValueError:
                return None

        def event_date(value: str):
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
            except ValueError:
                return None

        total_spend = sum(float(record.get("actual_spend") or 0) for record in records)
        upcoming = [
            record for record in records
            if (date_value(record.get("travel_start_date", "")) or today) >= today
            and record.get("booking_status") not in {"Completed", "Cancelled", "Rejected"}
        ]
        currently_traveling = [
            record for record in records
            if (date_value(record.get("travel_start_date", "")) or today) <= today
            and (date_value(record.get("travel_end_date", "")) or today) >= today
            and record.get("booking_status") not in {"Cancelled", "Rejected"}
        ]
        pending_approvals = [
            record for record in records
            if record.get("approval_status") in {"Submitted", "Pending Approval", "Needs Info"}
        ]
        over_budget = [record for record in records if record.get("policy_status") == "Over Budget"]
        todays_events = [event for event in events if event_date(event.get("start_datetime", "")) == today]

        employee_map: dict[str, dict[str, Any]] = {}
        department_spend: dict[str, float] = {}
        destination_map: dict[str, dict[str, Any]] = {}
        monthly_spend: dict[str, float] = {}
        for record in records:
            employee_key = record["employee_email"] or record["employee_name"]
            employee_entry = employee_map.setdefault(
                employee_key,
                {
                    "employee_name": record["employee_name"],
                    "employee_email": record["employee_email"],
                    "department": record["department"],
                    "travel_count": 0,
                    "trip_count": 0,
                    "actual_spend": 0.0,
                    "estimated_budget": 0.0,
                },
            )
            employee_entry["travel_count"] += 1
            employee_entry["trip_count"] += int(record.get("number_of_trips") or 0)
            employee_entry["actual_spend"] += float(record.get("actual_spend") or 0)
            employee_entry["estimated_budget"] += float(record.get("estimated_budget") or 0)

            department_spend[record["department"]] = department_spend.get(record["department"], 0.0) + float(record.get("actual_spend") or 0)
            destination_entry = destination_map.setdefault(
                record["destination_to"],
                {"destination": record["destination_to"], "travel_count": 0, "actual_spend": 0.0},
            )
            destination_entry["travel_count"] += 1
            destination_entry["actual_spend"] += float(record.get("actual_spend") or 0)

            month = str(record.get("travel_start_date", ""))[:7] or "Unknown"
            monthly_spend[month] = monthly_spend.get(month, 0.0) + float(record.get("actual_spend") or 0)

        return {
            "cards": {
                "total_travel_spend": total_spend,
                "upcoming_trips": len(upcoming),
                "currently_traveling_employees": len({record["employee_email"] for record in currently_traveling}),
                "pending_travel_approvals": len(pending_approvals),
                "over_budget_travel": len(over_budget),
                "todays_calendar_events": len(todays_events),
            },
            "travel_count_by_employee": sorted(employee_map.values(), key=lambda item: item["travel_count"], reverse=True),
            "travel_spend_by_employee": sorted(employee_map.values(), key=lambda item: item["actual_spend"], reverse=True),
            "travel_spend_by_department": [
                {"department": department, "actual_spend": spend}
                for department, spend in sorted(department_spend.items(), key=lambda item: item[1], reverse=True)
            ],
            "top_destinations": sorted(destination_map.values(), key=lambda item: item["travel_count"], reverse=True),
            "monthly_travel_spend": [
                {"month": month, "actual_spend": spend}
                for month, spend in sorted(monthly_spend.items())
            ],
        }

    def _next_travel_id(self) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT travel_id FROM travel_records WHERE travel_id LIKE 'TRV-%' ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if not row:
            return "TRV-1001"
        try:
            number = int(str(row["travel_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"TRV-{number}"

    def _next_calendar_event_id(self) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT event_id FROM calendar_events WHERE event_id LIKE 'CAL-%' ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if not row:
            return "CAL-1001"
        try:
            number = int(str(row["event_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"CAL-{number}"

    def add_report(self, report: dict, file_content: bytes) -> dict:
        self.ensure_report_schema()
        if not file_content:
            raise ValueError("Report file is empty")
        file_type = self._report_file_type(report["filename"])
        if not file_type:
            raise ValueError("Unsupported report file type")
        now = utc_now()
        report_id = report.get("report_id") or self._next_report_id()
        stored_file_path = self._store_report_file(
            report_id=report_id,
            original_filename=report["filename"],
            file_content=file_content,
        )
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (
                    report_id, report_name, report_type, department,
                    uploaded_by_user_id, uploaded_by_name, uploaded_by_email,
                    uploaded_by_role, uploaded_at, file_type, file_name,
                    stored_file_path, file_size, status, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    report["report_name"],
                    report["report_type"],
                    report["department"],
                    report.get("uploaded_by_user_id"),
                    report.get("uploaded_by_name", ""),
                    report.get("uploaded_by_email", ""),
                    report.get("uploaded_by_role", ""),
                    now,
                    file_type,
                    Path(report["filename"]).name,
                    str(stored_file_path),
                    len(file_content),
                    report.get("status", "Ready"),
                    report.get("notes", ""),
                    now,
                    now,
                ),
            )
            row_id = int(cursor.lastrowid)
        return self.get_report(row_id)

    def get_report(self, report_row_id: int) -> dict:
        self.ensure_report_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_row_id,)).fetchone()
        return self._report_from_row(row) if row else {}

    def list_reports(self) -> list[dict]:
        self.ensure_report_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM reports ORDER BY uploaded_at DESC, id DESC",
            ).fetchall()
        return [self._report_from_row(row) for row in rows]

    def delete_report(self, report_row_id: int) -> dict:
        self.ensure_report_schema()
        report = self.get_report(report_row_id)
        if not report:
            return {}
        stored_path = Path(report.get("stored_file_path", ""))
        with self.db.connection() as conn:
            conn.execute("DELETE FROM reports WHERE id = ?", (report_row_id,))
        try:
            if stored_path.exists() and stored_path.is_file():
                stored_path.unlink()
        except OSError:
            pass
        return report

    def seed_demo_reports(self) -> None:
        if self.list_reports():
            return

        def user(email: str) -> dict:
            found = self.get_user_by_email(email)
            if not found:
                raise ValueError(f"Demo user missing for report seed: {email}")
            return found

        demo_reports = [
            (
                {
                    "report_name": "IT Asset Summary",
                    "report_type": "Inventory",
                    "department": "IT",
                    "filename": "it_asset_summary.csv",
                    "notes": "Seeded IT report for report management demo.",
                    "uploader": user("it@company.com"),
                },
                b"asset_type,total,assigned\nLaptop,42,35\nPeripheral,80,50\n",
            ),
            (
                {
                    "report_name": "Finance Expense Snapshot",
                    "report_type": "Expense",
                    "department": "Finance",
                    "filename": "finance_expense_snapshot.csv",
                    "notes": "Seeded finance report for report management demo.",
                    "uploader": user("finance@company.com"),
                },
                b"category,total\nTravel,124500\nSoftware,68000\n",
            ),
            (
                {
                    "report_name": "Admin Operations Overview",
                    "report_type": "Operations",
                    "department": "Admin",
                    "filename": "admin_operations_overview.pdf",
                    "notes": "Seeded admin PDF placeholder for report management demo.",
                    "uploader": user("admin@company.com"),
                },
                b"%PDF-1.4\n% Agent Concierge demo report placeholder\n",
            ),
        ]
        for metadata, content in demo_reports:
            uploader = metadata.pop("uploader")
            self.add_report(
                {
                    **metadata,
                    "uploaded_by_user_id": uploader["id"],
                    "uploaded_by_name": uploader["name"],
                    "uploaded_by_email": uploader["email"],
                    "uploaded_by_role": uploader["role"],
                },
                content,
            )

    def _store_report_file(self, *, report_id: str, original_filename: str, file_content: bytes) -> Path:
        self.report_upload_dir.mkdir(parents=True, exist_ok=True)
        original = Path(original_filename).name
        extension = Path(original).suffix.lower()
        safe_stem = "".join(
            char if char.isalnum() or char in {"-", "_"} else "-"
            for char in Path(original).stem
        ).strip("-") or "report"
        stored_path = self.report_upload_dir / f"{report_id}-{safe_stem}{extension}"
        stored_path.write_bytes(file_content)
        return stored_path

    def _report_file_type(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if extension == ".csv":
            return "CSV"
        if extension == ".xlsx":
            return "XLSX"
        if extension == ".pdf":
            return "PDF"
        if extension == ".txt":
            return "TXT"
        if extension == ".md":
            return "MD"
        if extension == ".docx":
            return "DOCX"
        if extension == ".doc":
            return "DOC"
        return ""

    def _next_report_id(self) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT report_id FROM reports WHERE report_id LIKE 'RPT-%' ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if not row:
            return "RPT-1001"
        try:
            number = int(str(row["report_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"RPT-{number}"

    def add_ticket(self, ticket: dict) -> dict:
        self.ensure_ticket_schema()
        now = utc_now()
        ticket_id = ticket.get("ticket_id") or self._next_ticket_id(ticket["ticket_type"])
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tickets (
                    ticket_id, ticket_type, title, description, category, priority,
                    status, requester_user_id, requester_name, requester_email,
                    requester_role, assigned_role, assigned_team, due_date, approval_required,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    ticket["ticket_type"],
                    ticket["title"],
                    ticket.get("description", ""),
                    ticket["category"],
                    ticket["priority"],
                    ticket.get("status", "Open"),
                    ticket.get("requester_user_id"),
                    ticket["requester_name"],
                    ticket["requester_email"],
                    ticket.get("requester_role", ""),
                    ticket["assigned_role"],
                    ticket["assigned_team"],
                    str(ticket["due_date"]) if ticket.get("due_date") else "",
                    1 if ticket.get("approval_required") else 0,
                    now,
                    now,
                ),
            )
            row_id = int(cursor.lastrowid)
        return self.get_ticket(row_id)

    def get_ticket(self, ticket_id: int) -> dict:
        self.ensure_ticket_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._ticket_from_row(row) if row else {}

    def list_tickets(self) -> list[dict]:
        self.ensure_ticket_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC, id DESC",
            ).fetchall()
        return [self._ticket_from_row(row) for row in rows]

    def update_ticket(self, ticket_id: int, **updates: Any) -> dict:
        self.ensure_ticket_schema()
        allowed = {
            "ticket_type",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "assigned_role",
            "assigned_team",
            "due_date",
            "approval_required",
        }
        fields = [key for key in updates if key in allowed]
        if not fields:
            return self.get_ticket(ticket_id)
        assignments = ", ".join([f"{field} = ?" for field in fields])
        values = []
        for key in fields:
            if key == "approval_required":
                values.append(1 if updates[key] else 0)
            elif key == "due_date":
                values.append(str(updates[key]) if updates.get(key) else "")
            else:
                values.append(updates[key])
        values.extend([utc_now(), ticket_id])
        with self.db.connection() as conn:
            conn.execute(
                f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values),
            )
        return self.get_ticket(ticket_id)

    def update_ticket_status(self, ticket_id: int, status: str) -> dict:
        return self.update_ticket(ticket_id, status=status)

    def add_notification(self, notification: dict) -> dict:
        self.ensure_notification_schema()
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (
                    title, message, type, related_entity_type, related_entity_id,
                    user_id, target_role, read_user_ids_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification["title"],
                    notification["message"],
                    notification["type"],
                    notification["related_entity_type"],
                    str(notification["related_entity_id"]),
                    notification.get("user_id"),
                    _normalize_assigned_role(notification.get("target_role", "")),
                    _json(notification.get("read_user_ids", [])),
                    now,
                ),
            )
            notification_id = int(cursor.lastrowid)
        return self.get_notification(notification_id)

    def get_notification(self, notification_id: int) -> dict:
        self.ensure_notification_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return self._notification_from_row(row) if row else {}

    def list_notifications(self, limit: int = 100) -> list[dict]:
        self.ensure_notification_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._notification_from_row(row) for row in rows]

    def mark_notification_read(self, notification_id: int, user_id: int) -> dict:
        notification = self.get_notification(notification_id)
        if not notification:
            return {}
        read_user_ids = {int(item) for item in notification.get("read_user_ids", [])}
        read_user_ids.add(int(user_id))
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE notifications SET read_user_ids_json = ? WHERE id = ?",
                (_json(sorted(read_user_ids)), notification_id),
            )
        return self.get_notification(notification_id)

    def _next_task_id(self) -> str:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT task_id FROM tasks WHERE task_id LIKE 'TASK-%' ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if not row or not row["task_id"]:
            return "TASK-1001"
        try:
            number = int(str(row["task_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"TASK-{number}"

    def _next_ticket_id(self, ticket_type: str) -> str:
        prefix = "IT" if ticket_type == "IT" else "ADM"
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT ticket_id FROM tickets WHERE ticket_id LIKE ? ORDER BY id DESC LIMIT 1",
                (f"{prefix}-%",),
            ).fetchone()
        if not row:
            return f"{prefix}-1001"
        try:
            number = int(str(row["ticket_id"]).split("-", 1)[1]) + 1
        except (IndexError, ValueError):
            number = 1001
        return f"{prefix}-{number}"

    def add_audit_log(
        self,
        *,
        action: str,
        actor: str,
        status: str,
        approval_required: bool = False,
        approval_reason: str | None = None,
        details: dict | None = None,
    ) -> dict:
        now = utc_now()
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, action, actor, status, approval_required,
                    approval_reason, details_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    action,
                    actor,
                    status,
                    1 if approval_required else 0,
                    approval_reason,
                    _json(details or {}),
                ),
            )
            log_id = int(cursor.lastrowid)
        return self.get_audit_log(log_id)

    def get_audit_log(self, log_id: int) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM audit_logs WHERE id = ?", (log_id,)).fetchone()
        return self._audit_from_row(row) if row else {}

    def list_audit_logs(self, limit: int = 100) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._audit_from_row(row) for row in rows]

    def upsert_connector(
        self,
        user_id: int,
        connector_type: str,
        provider: str,
        status: str,
        display_name: str,
        config: dict | None = None,
        last_tested_at: str = "",
    ) -> dict:
        self.ensure_connector_schema()
        now = utc_now()
        with self.db.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM connectors WHERE user_id = ? AND connector_type = ?",
                (user_id, connector_type),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE connectors
                    SET provider = ?, status = ?, display_name = ?, config_json = ?,
                        last_tested_at = COALESCE(NULLIF(?, ''), last_tested_at), updated_at = ?
                    WHERE user_id = ? AND connector_type = ?
                    """,
                    (provider, status, display_name, _json(config or {}), last_tested_at, now, user_id, connector_type),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO connectors (
                        user_id, connector_type, provider, status, display_name, config_json,
                        last_tested_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, connector_type, provider, status, display_name, _json(config or {}), last_tested_at, now, now),
                )
        return self.get_connector(connector_type, user_id)

    def get_connector(self, connector_type: str, user_id: int | None = None) -> dict:
        self.ensure_connector_schema()
        with self.db.connection() as conn:
            if user_id is not None:
                row = conn.execute(
                    "SELECT * FROM connectors WHERE user_id = ? AND connector_type = ?",
                    (user_id, connector_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM connectors WHERE connector_type = ? ORDER BY updated_at DESC, id DESC LIMIT 1",
                    (connector_type,),
                ).fetchone()
        if row:
            return self._connector_from_row(row)
        if connector_type == "email":
            return {
                "id": None,
                "user_id": user_id,
                "connector_type": "email",
                "provider": "Mock Email",
                "status": "mock_mode",
                "display_name": "Email",
                "config": {},
                "last_tested_at": "",
                "created_at": "",
                "updated_at": "",
            }
        if connector_type == "whatsapp":
            return {
                "id": None,
                "user_id": user_id,
                "connector_type": "whatsapp",
                "provider": "Mock WhatsApp",
                "status": "mock_mode",
                "display_name": "WhatsApp",
                "config": {},
                "last_tested_at": "",
                "created_at": "",
                "updated_at": "",
            }
        return {}

    def list_connectors(self, user_id: int | None = None) -> list[dict]:
        return [self.get_connector("email", user_id), self.get_connector("whatsapp", user_id)]

    def disconnect_connector(self, user_id: int, connector_type: str) -> dict:
        display_name = "Email" if connector_type == "email" else "WhatsApp"
        provider = "Mock Email" if connector_type == "email" else "Mock WhatsApp"
        return self.upsert_connector(user_id, connector_type, provider, "not_connected", display_name, {}, "")

    def list_message_templates(self) -> list[dict]:
        self.ensure_connector_schema()
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM message_templates ORDER BY name ASC").fetchall()
        return [dict(row) for row in rows]

    def add_communication_log(self, log: dict) -> dict:
        self.ensure_connector_schema()
        now = utc_now()
        sent_at = log.get("sent_at") or now
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO communication_logs (
                    channel, recipient_name, recipient_email, recipient_phone,
                    subject, message_body, status, provider, related_module,
                    related_record_id, sent_by_user_id, sent_by_name,
                    sent_by_email, sent_at, error_message, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.get("channel", ""),
                    log.get("recipient_name", ""),
                    log.get("recipient_email", ""),
                    log.get("recipient_phone", ""),
                    log.get("subject", ""),
                    log.get("message_body", ""),
                    log.get("status", ""),
                    log.get("provider", ""),
                    log.get("related_module", ""),
                    str(log.get("related_record_id", "")),
                    log.get("sent_by_user_id"),
                    log.get("sent_by_name", ""),
                    log.get("sent_by_email", ""),
                    sent_at,
                    log.get("error_message", ""),
                    _json(log.get("metadata", {})),
                    now,
                ),
            )
            log_id = int(cursor.lastrowid)
        return self.get_communication_log(log_id)

    def get_communication_log(self, log_id: int) -> dict:
        self.ensure_connector_schema()
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM communication_logs WHERE id = ?", (log_id,)).fetchone()
        return self._communication_log_from_row(row) if row else {}

    def list_communication_logs(self, limit: int = 100) -> list[dict]:
        self.ensure_connector_schema()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM communication_logs ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._communication_log_from_row(row) for row in rows]

    def dashboard(self) -> dict:
        meetings = self.list_meetings(limit=5)
        tasks = self.list_tasks()
        pending_approvals = self.list_approvals(status="pending")
        notes = self.list_notes(limit=3)
        agent_plans = self.list_agent_plans(limit=3)
        routed_requests = self.list_routed_requests(limit=5)
        return {
            "meetings": meetings,
            "tasks": tasks,
            "pending_approvals": pending_approvals,
            "recent_notes": notes,
            "routed_requests": routed_requests,
            "agent_plans": agent_plans,
            "latest_agent_plan": agent_plans[0] if agent_plans else None,
            "metrics": {
                "meetings_scheduled": len(meetings),
                "open_tasks": len([task for task in tasks if str(task["status"]).lower() == "open"]),
                "pending_approvals": len(pending_approvals),
                "audit_events": len(self.list_audit_logs(limit=1000)),
            },
        }

    def _meeting_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["agenda"] = _loads(item.pop("agenda_json"), [])
        item["attendees"] = _loads(item.pop("attendees_json"), [])
        item["files"] = _loads(item.pop("files_json"), [])
        return item

    def _note_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["decisions"] = _loads(item.pop("decisions_json"), [])
        item["action_items"] = _loads(item.pop("action_items_json"), [])
        return item

    def _task_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["task_id"] = item.get("task_id") or f"TASK-{1000 + int(item['id'])}"
        item["description"] = item.get("description") or item.get("title", "")
        item["category"] = item.get("category") or ("Vendor" if item.get("source") == "meeting_action_item" else "Admin")
        item["department"] = item.get("department") or "Admin"
        item["assigned_to"] = item.get("assigned_to") or item.get("owner_name", "")
        item["assigned_user_id"] = item.get("assigned_user_id")
        item["assigned_email"] = item.get("assigned_email") or item.get("owner_email", "")
        item["assigned_role"] = _normalize_assigned_role(item.get("assigned_role", "admin"))
        item["priority"] = item.get("priority") or "Medium"
        item["status"] = self._normalize_task_status(item.get("status"))
        item["created_by_role"] = _normalize_role_value(item.get("created_by_role", ""))
        return item

    def _user_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["is_demo"] = bool(item.get("is_demo", False))
        item["role"] = _normalize_role_value(item["role"])
        return item

    def _approval_from_row(self, row: Any) -> dict:
        item = dict(row)
        metadata = ApprovalRulesService().approval_metadata(item["approval_type"])
        item["required_roles"] = metadata["required_roles"]
        item["required_role_label"] = metadata["required_role_label"]
        item["assigned_role"] = metadata["assigned_role"]
        item["task_type"] = metadata["task_type"]
        item["priority"] = metadata["priority"]
        item["risk_level"] = metadata["risk_level"]
        item["approval_required"] = metadata["approval_required"]
        return item

    def _routed_request_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["assigned_role"] = _normalize_assigned_role(item["assigned_role"])
        item["required_approval_roles"] = _loads(
            item.pop("required_approval_roles_json"),
            [],
        )
        item["required_approval_roles"] = [
            _normalize_assigned_role(role) for role in item["required_approval_roles"]
        ]
        item["approval_required"] = bool(item["approval_required"])
        item["required_role_label"] = ApprovalRulesService().approval_metadata(
            item["approval_type"] or "",
        )["required_role_label"] if item["approval_required"] else "No approval required"
        return item

    def _vendor_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["billing_amount"] = int(item.get("billing_amount") or 0)
        return item

    def _ticket_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["approval_required"] = bool(item["approval_required"])
        item["requester_role"] = _normalize_role_value(item.get("requester_role", ""))
        item["assigned_role"] = _normalize_assigned_role(item["assigned_role"])
        return item

    def _notification_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["target_role"] = _normalize_assigned_role(item.get("target_role", ""))
        item["read_user_ids"] = [int(user_id) for user_id in _loads(item.pop("read_user_ids_json"), [])]
        return item

    def _expense_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["amount"] = float(item.get("amount") or 0)
        item["approval_required"] = bool(item["approval_required"])
        item["employee_role"] = _normalize_role_value(item.get("employee_role", ""))
        item["policy_exceptions"] = _loads(item.pop("policy_exceptions_json"), [])
        return item

    def _inventory_item_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["quantity"] = int(item.get("quantity") or 0)
        item["minimum_stock_level"] = int(item.get("minimum_stock_level") or 0)
        item["import_batch_id"] = item.get("import_batch_id")
        item["employee_name"] = item.get("employee_name") or item.get("assigned_to") or ""
        item["serial_no"] = item.get("serial_no") or item.get("serial_number") or ""
        item["model_no"] = item.get("model_no") or item.get("model") or ""
        item["ram"] = item.get("ram") or ""
        item["disk"] = item.get("disk") or ""
        return item

    def _inventory_import_batch_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["total_rows"] = int(item.get("total_rows") or 0)
        item["successful_rows"] = int(item.get("successful_rows") or 0)
        item["failed_rows"] = int(item.get("failed_rows") or 0)
        item["is_legacy_unbatched"] = False
        return item

    def _travel_record_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["estimated_budget"] = float(item.get("estimated_budget") or 0)
        item["actual_spend"] = float(item.get("actual_spend") or 0)
        item["number_of_trips"] = int(item.get("number_of_trips") or 0)
        return item

    def _calendar_event_from_row(self, row: Any) -> dict:
        return dict(row)

    def _report_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["file_size"] = int(item.get("file_size") or 0)
        item["uploaded_by_role"] = _normalize_role_value(item.get("uploaded_by_role", ""))
        return item

    def _connector_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["config"] = _loads(item.pop("config_json"), {})
        return item

    def _communication_log_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["metadata"] = _loads(item.pop("metadata_json"), {})
        return item

    def _audit_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["approval_required"] = bool(item["approval_required"])
        item["details"] = _loads(item.pop("details_json"), {})
        return item

    def _agent_plan_from_row(self, row: Any) -> dict:
        item = dict(row)
        item["approval_required"] = bool(item["approval_required"])
        item["plan"] = _loads(item.pop("plan_json"), {})
        if "required_tools" not in item["plan"] and "required_mock_tools" in item["plan"]:
            item["plan"]["required_tools"] = item["plan"].pop("required_mock_tools")
        return item
