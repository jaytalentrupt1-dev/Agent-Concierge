from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


Role = Literal["admin", "it_manager", "finance_manager", "employee"]

RouteTaskType = Literal[
    "meeting_management",
    "vendor_management",
    "expense_management",
    "travel_management",
    "inventory_management",
    "it_request",
    "document_management",
    "report_generation",
    "floor_activity_management",
]


class CommandRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


class ChatbotRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = str(value or "").strip()
        if not value:
            raise ValueError("Message is required")
        return value


class RouteRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)
    task_type: RouteTaskType | None = None
    approval_type: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    action: Literal["approve_send", "edit", "cancel"]
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=500)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=200)
    role: str


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    role: str | None = None
    enabled: bool | None = None


class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=6, max_length=200)


class VendorCreateRequest(BaseModel):
    vendor_name: str = Field(min_length=2, max_length=160)
    contact_person: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    contact_details: str = Field(min_length=3, max_length=80)
    office_address: str = Field(min_length=5, max_length=500)
    service_provided: Literal[
        "Transport",
        "Food",
        "Office Supplies",
        "IT Services",
        "Security",
        "Housekeeping",
        "Other",
    ]
    start_date: date
    end_date: date | None = None
    billing_amount: int = Field(gt=0)
    billing_cycle: Literal["Monthly", "Quarterly", "Half-yearly", "Yearly"]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("end_date", mode="before")
    @classmethod
    def normalize_empty_end_date(cls, value):
        if value == "":
            return None
        return value

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: date | None, info) -> date | None:
        if value is None:
            return value
        start_date = info.data.get("start_date")
        if start_date and value < start_date:
            raise ValueError("Vendor end date must be on or after start date")
        return value


class VendorUpdateRequest(VendorCreateRequest):
    pass


class VendorEmailRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=4000)


ConnectorType = Literal["email", "whatsapp"]
CommunicationChannel = Literal["email", "whatsapp", "both"]


class EmailConnectorConfigRequest(BaseModel):
    provider: Literal["SMTP", "SendGrid", "Mock Email"] = "Mock Email"
    from_name: str = Field(default="Agent Concierge", max_length=120)
    from_email: str = Field(default="", max_length=254)
    smtp_host: str = Field(default="", max_length=180)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str = Field(default="", max_length=180)
    smtp_password: str = Field(default="", max_length=500)
    sendgrid_api_key: str = Field(default="", max_length=500)
    reply_to_email: str = Field(default="", max_length=254)

    @field_validator("from_name", "from_email", "smtp_host", "smtp_username", "smtp_password", "sendgrid_api_key", "reply_to_email")
    @classmethod
    def trim_email_config(cls, value: str) -> str:
        return value.strip()


class WhatsAppConnectorConfigRequest(BaseModel):
    provider: Literal["Twilio WhatsApp", "WhatsApp Cloud API", "Mock WhatsApp"] = "Mock WhatsApp"
    business_phone_number: str = Field(default="", max_length=80)
    twilio_account_sid: str = Field(default="", max_length=180)
    twilio_auth_token: str = Field(default="", max_length=500)
    twilio_whatsapp_sender_number: str = Field(default="", max_length=80)
    whatsapp_cloud_api_access_token: str = Field(default="", max_length=500)
    whatsapp_phone_number_id: str = Field(default="", max_length=180)
    whatsapp_business_account_id: str = Field(default="", max_length=180)

    @field_validator(
        "business_phone_number",
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_whatsapp_sender_number",
        "whatsapp_cloud_api_access_token",
        "whatsapp_phone_number_id",
        "whatsapp_business_account_id",
    )
    @classmethod
    def trim_whatsapp_config(cls, value: str) -> str:
        return value.strip()


class ConnectorDisconnectRequest(BaseModel):
    connector_type: ConnectorType


class CommunicationSendRequest(BaseModel):
    recipient_name: str = Field(default="", max_length=160)
    recipient_email: str = Field(default="", max_length=254)
    recipient_phone: str = Field(default="", max_length=80)
    subject: str = Field(default="", max_length=220)
    message_body: str = Field(min_length=1, max_length=5000)
    attachments: list[str] = Field(default_factory=list, max_length=10)
    related_module: str = Field(default="general", max_length=80)
    related_record_id: str = Field(default="", max_length=120)
    channel: CommunicationChannel = "email"

    @field_validator("recipient_name", "recipient_email", "recipient_phone", "subject", "message_body", "related_module", "related_record_id")
    @classmethod
    def trim_message_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("attachments")
    @classmethod
    def trim_attachments(cls, value: list[str]) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()]


TicketType = Literal["IT", "Admin"]
TicketStatus = Literal["Open", "In Progress", "Waiting Approval", "Resolved", "Closed"]
TicketPriority = Literal["Low", "Medium", "High", "Critical"]
TaskCategory = Literal["Admin", "IT", "Finance", "Vendor", "Inventory", "Travel", "Expense", "Report", "Other"]
TaskPriority = Literal["Low", "Medium", "High", "Critical"]
TaskStatus = Literal["Open", "In Progress", "Waiting Approval", "Completed", "Cancelled"]
ExpenseCategory = Literal[
    "Travel",
    "Food",
    "Hotel",
    "Local Conveyance",
    "Office Supplies",
    "Software",
    "Internet / Phone",
    "Vendor Payment",
    "Client Meeting",
    "Training",
    "Miscellaneous",
]
ExpenseStatus = Literal[
    "Draft",
    "Submitted",
    "Pending Approval",
    "Approved",
    "Rejected",
    "Paid",
    "Reimbursed",
    "Needs Info",
]
InventoryCategory = Literal[
    "IT Equipment",
    "Stationery Equipment",
    "Festival Equipment",
    "Onboarding Equipment",
    "Other",
]
TravelMode = Literal["Flight", "Train", "Bus", "Cab", "Hotel", "Mixed", "Other"]
TravelStatus = Literal[
    "Draft",
    "Submitted",
    "Pending Approval",
    "Approved",
    "Rejected",
    "Booked",
    "Completed",
    "Cancelled",
    "Needs Info",
]
TravelPolicyStatus = Literal["Within Policy", "Over Budget", "Missing Approval", "Needs Review"]
CalendarEventType = Literal["Meeting", "Vendor Meeting", "Travel", "Reminder", "Internal Event", "Other"]
CalendarEventStatus = Literal["Scheduled", "Completed", "Cancelled", "Tentative"]


class TicketCreateRequest(BaseModel):
    ticket_type: TicketType = Field(validation_alias=AliasChoices("ticket_type", "type"))
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=1000)
    category: str = Field(min_length=2, max_length=100)
    priority: TicketPriority
    status: TicketStatus = "Open"
    due_date: date | None = None
    approval_required: bool = False

    @field_validator("due_date", mode="before")
    @classmethod
    def normalize_empty_due_date(cls, value):
        if value == "":
            return None
        return value


class TicketUpdateRequest(TicketCreateRequest):
    pass


class TicketStatusUpdateRequest(BaseModel):
    status: TicketStatus


class TaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=1000)
    category: TaskCategory
    department: str = Field(min_length=2, max_length=120)
    assigned_to: str = Field(default="", max_length=160)
    assigned_user_id: int | None = None
    assigned_email: str = Field(default="", max_length=254)
    assigned_role: Role
    priority: TaskPriority
    status: TaskStatus = "Open"
    due_date: date | None = None
    notes: str = Field(default="", max_length=1000)

    @field_validator("due_date", mode="before")
    @classmethod
    def normalize_empty_task_due_date(cls, value):
        if value == "":
            return None
        return value

    @field_validator("title", "description", "department", "assigned_to", "assigned_email", "notes")
    @classmethod
    def trim_task_text(cls, value: str) -> str:
        return value.strip()


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class ExpenseCreateRequest(BaseModel):
    employee_name: str = Field(default="", max_length=120)
    employee_email: str = Field(default="", max_length=254)
    department: str = Field(min_length=2, max_length=120)
    category: ExpenseCategory
    vendor_merchant: str = Field(min_length=2, max_length=160)
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=2, max_length=8)
    expense_date: date
    payment_mode: str = Field(min_length=2, max_length=80)
    receipt_status: Literal["Attached", "Missing", "Pending", "Not Required"]
    receipt_attachment_name: str = Field(default="", max_length=220)
    notes: str = Field(default="", max_length=1000)
    status: ExpenseStatus = "Draft"
    approval_required: bool = False

    @field_validator(
        "employee_name",
        "employee_email",
        "department",
        "vendor_merchant",
        "currency",
        "payment_mode",
        "receipt_attachment_name",
        "notes",
    )
    @classmethod
    def trim_expense_text(cls, value: str) -> str:
        return value.strip()


class ExpenseUpdateRequest(ExpenseCreateRequest):
    pass


class ExpenseImportItemRequest(ExpenseCreateRequest):
    expense_id: str = Field(min_length=2, max_length=80)


class ExpenseImportPreviewRequest(BaseModel):
    filename: str = Field(min_length=3, max_length=260)
    content_base64: str = Field(min_length=1)


class ExpenseImportConfirmRequest(BaseModel):
    filename: str = Field(min_length=3, max_length=260)
    items: list[ExpenseImportItemRequest] = Field(min_length=1, max_length=5000)


class ExpenseStatusUpdateRequest(BaseModel):
    status: ExpenseStatus


class InventoryItemRequest(BaseModel):
    item_id: str = Field(default="", max_length=80)
    item_name: str = Field(default="", max_length=160)
    category: InventoryCategory = "Other"
    subcategory: str = Field(default="", max_length=120)
    brand: str = Field(default="", max_length=120)
    model: str = Field(default="", max_length=120)
    serial_number: str = Field(default="", max_length=160)
    quantity: int = Field(default=1, ge=0)
    unit: str = Field(default="unit", max_length=40)
    condition: str = Field(default="Good", max_length=80)
    location: str = Field(default="", max_length=160)
    assigned_to: str = Field(default="", max_length=160)
    department: str = Field(default="", max_length=120)
    purchase_date: date | None = None
    warranty_end_date: date | None = None
    vendor: str = Field(default="", max_length=160)
    minimum_stock_level: int = Field(default=0, ge=0)
    employee_name: str = Field(default="", max_length=160)
    serial_no: str = Field(default="", max_length=160)
    model_no: str = Field(default="", max_length=120)
    ram: str = Field(default="", max_length=80)
    disk: str = Field(default="", max_length=80)
    status: str = Field(min_length=2, max_length=80)
    notes: str = Field(default="", max_length=1000)

    @field_validator("purchase_date", "warranty_end_date", mode="before")
    @classmethod
    def normalize_empty_dates(cls, value):
        if value == "":
            return None
        return value

    @field_validator(
        "item_id",
        "item_name",
        "subcategory",
        "brand",
        "model",
        "serial_number",
        "employee_name",
        "serial_no",
        "model_no",
        "ram",
        "disk",
        "unit",
        "condition",
        "location",
        "assigned_to",
        "department",
        "vendor",
        "status",
        "notes",
    )
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_inventory_identity(self):
        has_new_shape = any([self.employee_name, self.serial_no, self.model_no, self.ram, self.disk])
        if has_new_shape:
            if not any([self.employee_name, self.serial_no, self.model_no]):
                raise ValueError("At least one of employee_name, serial_no, or model_no is required")
        elif not self.item_name:
            raise ValueError("Item name is required")
        return self


class InventoryImportPreviewRequest(BaseModel):
    filename: str = Field(min_length=3, max_length=260)
    content_base64: str = Field(min_length=1)


class InventoryBulkDeleteRequest(BaseModel):
    item_ids: list[int | str] = Field(min_length=1, max_length=5000)
    selection_mode: str | None = Field(default=None, max_length=80)
    search: str | None = Field(default=None, max_length=300)
    filters: dict[str, Any] = Field(default_factory=dict)


class InventoryStatusUpdateRequest(BaseModel):
    status: Literal["In Use", "Extra", "Submitted to Vendor"]


class InventoryImportCreateRequest(BaseModel):
    filename: str = Field(min_length=3, max_length=260)
    items: list[InventoryItemRequest] = Field(min_length=1, max_length=5000)


class TravelRecordRequest(BaseModel):
    travel_id: str = Field(default="", max_length=80)
    employee_name: str = Field(min_length=2, max_length=120)
    employee_email: str = Field(min_length=3, max_length=254)
    department: str = Field(min_length=2, max_length=120)
    destination_from: str = Field(min_length=2, max_length=160)
    destination_to: str = Field(min_length=2, max_length=160)
    travel_start_date: date
    travel_end_date: date
    purpose: str = Field(min_length=2, max_length=220)
    travel_mode: TravelMode
    estimated_budget: float = Field(ge=0)
    actual_spend: float = Field(ge=0)
    number_of_trips: int = Field(ge=1)
    approval_status: TravelStatus = "Draft"
    policy_status: TravelPolicyStatus = "Within Policy"
    booking_status: TravelStatus = "Draft"
    notes: str = Field(default="", max_length=1000)
    google_calendar_event_id: str = Field(default="", max_length=180)
    google_sync_status: str = Field(default="Not Synced", max_length=80)
    google_last_synced_at: datetime | None = None

    @field_validator("employee_email")
    @classmethod
    def validate_travel_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid employee email address")
        return normalized

    @field_validator("travel_id", "employee_name", "department", "destination_from", "destination_to", "purpose", "notes", "google_calendar_event_id", "google_sync_status")
    @classmethod
    def trim_travel_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("google_last_synced_at", mode="before")
    @classmethod
    def normalize_empty_google_synced_at(cls, value):
        if value == "":
            return None
        return value

    @field_validator("travel_end_date")
    @classmethod
    def validate_travel_end_date(cls, value: date, info) -> date:
        start_date = info.data.get("travel_start_date")
        if start_date and value < start_date:
            raise ValueError("Travel end date must be on or after start date")
        return value


class CalendarEventRequest(BaseModel):
    event_id: str = Field(default="", max_length=80)
    title: str = Field(min_length=2, max_length=180)
    event_type: CalendarEventType
    start_datetime: datetime
    end_datetime: datetime
    location: str = Field(default="", max_length=180)
    attendees: str = Field(default="", max_length=500)
    related_travel_id: str = Field(default="", max_length=80)
    reminder: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=1000)
    status: CalendarEventStatus = "Scheduled"
    google_calendar_event_id: str = Field(default="", max_length=180)
    google_sync_status: str = Field(default="Not Synced", max_length=80)
    google_last_synced_at: datetime | None = None

    @field_validator("event_id", "title", "location", "attendees", "related_travel_id", "reminder", "notes", "google_calendar_event_id", "google_sync_status")
    @classmethod
    def trim_event_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("google_last_synced_at", mode="before")
    @classmethod
    def normalize_empty_event_google_synced_at(cls, value):
        if value == "":
            return None
        return value

    @field_validator("end_datetime")
    @classmethod
    def validate_event_end_datetime(cls, value: datetime, info) -> datetime:
        start_datetime = info.data.get("start_datetime")
        if start_datetime and value < start_datetime:
            raise ValueError("Event end time must be on or after start time")
        return value


class ReportImportRequest(BaseModel):
    report_name: str = Field(min_length=2, max_length=180)
    report_type: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=1000)
    filename: str = Field(min_length=3, max_length=260)
    content_base64: str = Field(min_length=1)

    @field_validator("report_name", "report_type", "department", "notes", "filename")
    @classmethod
    def trim_report_text(cls, value: str) -> str:
        return value.strip()
