from __future__ import annotations

import re
from datetime import date

from app.services.inventory_import import parse_tabular_file


EXPENSE_CATEGORIES = {
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
}

EXPENSE_STATUSES = {
    "Draft",
    "Submitted",
    "Pending Approval",
    "Approved",
    "Rejected",
    "Paid",
    "Reimbursed",
    "Needs Info",
}

RECEIPT_STATUSES = {"Attached", "Missing", "Pending", "Not Required"}

HEADER_MAP = {
    "expenseid": "expense_id",
    "id": "expense_id",
    "employeename": "employee_name",
    "employee": "employee_name",
    "employeeemail": "employee_email",
    "email": "employee_email",
    "department": "department",
    "category": "category",
    "vendorormerchant": "vendor_merchant",
    "vendormerchant": "vendor_merchant",
    "merchant": "vendor_merchant",
    "vendor": "vendor_merchant",
    "amount": "amount",
    "currency": "currency",
    "expensedate": "expense_date",
    "date": "expense_date",
    "paymentmode": "payment_mode",
    "receiptstatus": "receipt_status",
    "receiptattachmentname": "receipt_attachment_name",
    "receiptattachment": "receipt_attachment_name",
    "notes": "notes",
    "status": "status",
    "approvalrequired": "approval_required",
}

EMPTY_EXPENSE = {
    "expense_id": "",
    "employee_name": "",
    "employee_email": "",
    "department": "",
    "category": "Miscellaneous",
    "vendor_merchant": "Unknown Merchant",
    "amount": "",
    "currency": "INR",
    "expense_date": "",
    "payment_mode": "Other",
    "receipt_status": "Pending",
    "receipt_attachment_name": "",
    "notes": "",
    "status": "Draft",
    "approval_required": False,
}

REQUIRED_FIELDS = {
    "expense_id": "Expense ID",
    "employee_name": "Employee name",
    "employee_email": "Employee email",
    "department": "Department",
    "category": "Category",
    "amount": "Amount",
    "expense_date": "Expense date",
    "status": "Status",
}


def preview_expense_file(filename: str, content_base64: str) -> dict:
    rows, file_type = parse_tabular_file(filename, content_base64)
    return _build_preview(rows, filename=filename, file_type=file_type)


def _build_preview(rows: list[list[str]], *, filename: str, file_type: str) -> dict:
    if len(rows) < 2:
        return {
            "file_name": filename,
            "file_type": file_type,
            "rows": [],
            "errors": ["File must include a header row and at least one expense row."],
            "warnings": [],
        }

    header_keys = [_header_key(header) for header in rows[0]]
    known_headers = {key for key in header_keys if key}
    missing_required_headers = [key for key in REQUIRED_FIELDS if key not in known_headers]
    errors: list[str] = []
    warnings: list[str] = []
    if missing_required_headers:
        errors.append("This file does not match the expense import template. Please use the expected expense columns.")

    parsed_rows = []
    for index, row in enumerate(rows[1:], start=2):
        if not any(str(cell).strip() for cell in row):
            continue
        expense = dict(EMPTY_EXPENSE)
        for column_index, value in enumerate(row):
            if column_index >= len(header_keys):
                continue
            key = header_keys[column_index]
            if key:
                expense[key] = str(value or "").strip()
        row_warnings = [] if missing_required_headers else _normalize_import_expense(expense)
        row_errors = [] if missing_required_headers else _validate_import_expense(expense)
        parsed_rows.append(
            {
                "rowNumber": index,
                "expense": expense,
                "errors": row_errors,
                "warnings": row_warnings,
            }
        )
        errors.extend(f"Row {index}: {message}" for message in row_errors)
        warnings.extend(f"Row {index}: {message}" for message in row_warnings)

    if not parsed_rows:
        errors.append("File must include at least one expense row.")

    return {
        "file_name": filename,
        "file_type": file_type,
        "rows": parsed_rows,
        "errors": errors,
        "warnings": warnings,
    }


def _normalize_import_expense(expense: dict[str, str | bool]) -> list[str]:
    warnings = []
    category = str(expense.get("category", "")).strip()
    matched_category = _match_choice(category, EXPENSE_CATEGORIES)
    if not matched_category:
        warnings.append(f'Category "{category or "blank"}" defaulted to Miscellaneous')
        expense["category"] = "Miscellaneous"
    else:
        expense["category"] = matched_category

    status = str(expense.get("status", "")).strip()
    matched_status = _match_choice(status, EXPENSE_STATUSES)
    if matched_status:
        expense["status"] = matched_status

    receipt_status = str(expense.get("receipt_status", "")).strip()
    expense["receipt_status"] = _match_choice(receipt_status, RECEIPT_STATUSES) or "Pending"

    if not str(expense.get("currency", "")).strip():
        expense["currency"] = "INR"
    else:
        expense["currency"] = str(expense["currency"]).strip().upper()
    if not str(expense.get("vendor_merchant", "")).strip():
        expense["vendor_merchant"] = "Unknown Merchant"
        warnings.append("Vendor/Merchant defaulted to Unknown Merchant")
    if not str(expense.get("payment_mode", "")).strip():
        expense["payment_mode"] = "Other"
    expense["expense_date"] = _normalize_date(str(expense.get("expense_date", "")).strip())
    expense["approval_required"] = str(expense.get("approval_required", "")).strip()
    return warnings


def _validate_import_expense(expense: dict[str, str | bool]) -> list[str]:
    errors = []
    for key, label in REQUIRED_FIELDS.items():
        if not str(expense.get(key, "")).strip():
            errors.append(f"{label} is required")
    email = str(expense.get("employee_email", "")).strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors.append("Employee email must be valid")
    amount = _parse_amount(str(expense.get("amount", "")).strip())
    if amount is None or amount <= 0:
        errors.append("Amount must be numeric and greater than 0")
    else:
        expense["amount"] = str(amount)
    if expense.get("expense_date") and not _is_iso_date(str(expense["expense_date"])):
        errors.append("Expense date must be valid")
    status = str(expense.get("status", "")).strip()
    if status and status not in EXPENSE_STATUSES:
        errors.append("Status must be one of the supported expense statuses")
    approval_value = str(expense.get("approval_required", "")).strip()
    parsed_approval = _parse_bool(approval_value)
    if approval_value and parsed_approval is None:
        errors.append("Approval required must be true or false")
    else:
        expense["approval_required"] = bool(parsed_approval)
    return errors


def _parse_amount(value: str) -> float | None:
    cleaned = re.sub(r"[^0-9.\-]", "", value.replace(",", ""))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_bool(value: str) -> bool | None:
    if value == "":
        return False
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    return None


def _normalize_date(value: str) -> str:
    if not value:
        return ""
    if _is_iso_date(value):
        return value
    for pattern in (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", r"^(\d{1,2})-(\d{1,2})-(\d{4})$"):
        match = re.match(pattern, value)
        if not match:
            continue
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return value
    return value


def _is_iso_date(value: str) -> bool:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    if not match:
        return False
    try:
        date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


def _match_choice(value: str, choices: set[str]) -> str:
    normalized = value.strip().lower()
    for choice in choices:
        if choice.lower() == normalized:
            return choice
    return ""


def _header_key(header: str) -> str:
    return HEADER_MAP.get(re.sub(r"[^a-z0-9]+", "", str(header).lower()), "")
