from __future__ import annotations

import base64
import csv
import io
import posixpath
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


INVENTORY_CATEGORIES = {
    "IT Equipment",
    "Stationery Equipment",
    "Festival Equipment",
    "Onboarding Equipment",
    "Other",
}

HEADER_MAP = {
    "employeename": "employee_name",
    "employee": "employee_name",
    "serialno": "serial_no",
    "serial": "serial_no",
    "modelno": "model_no",
    "modelnumber": "model_no",
    "ram": "ram",
    "memory": "ram",
    "disk": "disk",
    "storage": "disk",
    "itemid": "item_id",
    "id": "item_id",
    "itemname": "item_name",
    "name": "item_name",
    "category": "category",
    "subcategory": "subcategory",
    "brand": "brand",
    "model": "model",
    "serialnumber": "serial_number",
    "quantity": "quantity",
    "qty": "quantity",
    "unit": "unit",
    "condition": "condition",
    "location": "location",
    "assignedto": "assigned_to",
    "department": "department",
    "purchasedate": "purchase_date",
    "warrantyenddate": "warranty_end_date",
    "vendor": "vendor",
    "minimumstocklevel": "minimum_stock_level",
    "minstock": "minimum_stock_level",
    "status": "status",
    "notes": "notes",
}

EMPTY_INVENTORY_ITEM = {
    "item_id": "",
    "item_name": "",
    "category": "Other",
    "subcategory": "",
    "brand": "",
    "model": "",
    "serial_number": "",
    "quantity": "",
    "unit": "pcs",
    "condition": "Good",
    "location": "",
    "assigned_to": "",
    "department": "",
    "purchase_date": "",
    "warranty_end_date": "",
    "vendor": "",
    "minimum_stock_level": "0",
    "employee_name": "",
    "serial_no": "",
    "model_no": "",
    "ram": "",
    "disk": "",
    "status": "In Use",
    "notes": "",
}

NEW_REQUIRED_FIELDS = {
    "employee_name": "Employee name",
    "serial_no": "Serial No.",
    "model_no": "Model No.",
    "ram": "RAM",
    "disk": "Disk",
    "location": "Location",
    "status": "Status",
}

LEGACY_REQUIRED_FIELDS = {
    "item_id": "Item ID",
    "item_name": "Item name",
    "category": "Category",
    "quantity": "Quantity",
    "unit": "Unit",
    "condition": "Condition",
    "location": "Location",
    "department": "Department",
    "minimum_stock_level": "Minimum stock level",
    "status": "Status",
}

BUILTIN_DATE_FORMAT_IDS = {
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    45,
    46,
    47,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
}


def parse_tabular_file(filename: str, content_base64: str) -> tuple[list[list[str]], str]:
    try:
        file_bytes = base64.b64decode(content_base64, validate=True)
    except ValueError as exc:
        raise ValueError("Could not read the uploaded file content.") from exc
    if not file_bytes:
        raise ValueError("Selected file is empty.")

    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        rows = _parse_csv(file_bytes)
    elif extension == ".xlsx":
        rows = _parse_xlsx(file_bytes)
    elif extension == ".xls":
        raise ValueError("Legacy .xls import is not enabled yet. Please use CSV or .xlsx.")
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or .xlsx file.")
    return rows, extension.removeprefix(".")


def preview_inventory_file(filename: str, content_base64: str) -> dict:
    rows, file_type = parse_tabular_file(filename, content_base64)
    return _build_preview(rows, filename=filename, file_type=file_type)


def _parse_csv(file_bytes: bytes) -> list[list[str]]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded.") from exc
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(text))
        if any(cell.strip() for cell in row)
    ]
    if not rows:
        raise ValueError("Selected file is empty.")
    return rows


def _parse_xlsx(file_bytes: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as workbook:
            worksheet_path = _first_worksheet_path(workbook)
            shared_strings = _shared_strings(workbook)
            date_style_indexes = _date_style_indexes(workbook)
            sheet = ElementTree.fromstring(workbook.read(worksheet_path))
    except (KeyError, ElementTree.ParseError, zipfile.BadZipFile) as exc:
        raise ValueError("Excel file could not be parsed. Please upload a valid .xlsx file.") from exc

    rows = []
    for row_element in _children_by_local_name(_first_by_local_name(sheet, "sheetData"), "row"):
        row_values: list[str] = []
        for cell in _children_by_local_name(row_element, "c"):
            reference = cell.attrib.get("r", "")
            column_index = _column_index(reference)
            if column_index is None:
                column_index = len(row_values)
            while len(row_values) <= column_index:
                row_values.append("")
            row_values[column_index] = _xlsx_cell_value(cell, shared_strings, date_style_indexes)
        if any(value.strip() for value in row_values):
            rows.append(row_values)
    if not rows:
        raise ValueError("Selected file is empty.")
    return rows


def _first_worksheet_path(workbook: zipfile.ZipFile) -> str:
    workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    first_sheet = _first_by_local_name(workbook_xml, "sheet")
    if first_sheet is None:
        raise ValueError("Excel file has no worksheet.")
    relationship_id = (
        first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        or first_sheet.attrib.get("r:id")
    )
    if not relationship_id:
        raise ValueError("Excel worksheet relationship is missing.")
    rels = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    target = ""
    for rel in _children_by_local_name(rels, "Relationship"):
        if rel.attrib.get("Id") == relationship_id:
            target = rel.attrib.get("Target", "")
            break
    if not target:
        raise ValueError("Excel worksheet target is missing.")
    if target.startswith("/"):
        normalized = target.lstrip("/")
    else:
        normalized = posixpath.normpath(posixpath.join("xl", target))
    return normalized


def _shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings = []
    for item in _children_by_local_name(root, "si"):
        strings.append("".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t"))
    return strings


def _date_style_indexes(workbook: zipfile.ZipFile) -> set[int]:
    try:
        root = ElementTree.fromstring(workbook.read("xl/styles.xml"))
    except KeyError:
        return set()
    date_format_ids = set(BUILTIN_DATE_FORMAT_IDS)
    for num_format in _children_by_local_name(_first_by_local_name(root, "numFmts"), "numFmt"):
        try:
            format_id = int(num_format.attrib.get("numFmtId", ""))
        except ValueError:
            continue
        format_code = num_format.attrib.get("formatCode", "").lower()
        if re.search(r"[ymdhHsS]", format_code):
            date_format_ids.add(format_id)
    styles = set()
    cell_xfs = _first_by_local_name(root, "cellXfs")
    for index, xf in enumerate(_children_by_local_name(cell_xfs, "xf")):
        try:
            format_id = int(xf.attrib.get("numFmtId", ""))
        except ValueError:
            continue
        if format_id in date_format_ids:
            styles.add(index)
    return styles


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str], date_style_indexes: set[int]) -> str:
    cell_type = cell.attrib.get("t", "")
    value_node = _first_by_local_name(cell, "v")
    if cell_type == "inlineStr":
        return " ".join(node.text or "" for node in cell.iter() if _local_name(node.tag) == "t").strip()
    if value_node is None or value_node.text is None:
        return ""
    value = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(value)].strip()
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    if _cell_uses_date_style(cell, date_style_indexes):
        converted = _excel_serial_to_date(value)
        if converted:
            return converted
    return _clean_number(value)


def _cell_uses_date_style(cell: ElementTree.Element, date_style_indexes: set[int]) -> bool:
    try:
        return int(cell.attrib.get("s", "")) in date_style_indexes
    except ValueError:
        return False


def _excel_serial_to_date(value: str) -> str:
    try:
        serial = float(value)
    except ValueError:
        return ""
    if serial <= 0:
        return ""
    return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()


def _clean_number(value: str) -> str:
    if re.fullmatch(r"-?\d+\.0+", value):
        return value.split(".", 1)[0]
    return value


def _build_preview(rows: list[list[str]], *, filename: str, file_type: str) -> dict:
    if len(rows) < 2:
        return {
            "file_name": filename,
            "file_type": file_type,
            "rows": [],
            "errors": ["File must include a header row and at least one item row."],
            "warnings": [],
        }
    header_keys = [_header_key(header) for header in rows[0]]
    parsed_rows = []
    errors: list[str] = []
    warnings: list[str] = []
    known_headers = {key for key in header_keys if key}
    has_new_template = any(key in known_headers for key in ["employee_name", "serial_no", "model_no", "ram", "disk"])
    required_fields = NEW_REQUIRED_FIELDS if has_new_template else LEGACY_REQUIRED_FIELDS
    missing_required_headers = [key for key in required_fields if key not in known_headers]
    if missing_required_headers:
        errors.append("This file does not match the inventory template. Please download and use the sample template.")

    for index, row in enumerate(rows[1:], start=2):
        if not any(str(cell).strip() for cell in row):
            continue
        item = dict(EMPTY_INVENTORY_ITEM)
        for column_index, value in enumerate(row):
            if column_index >= len(header_keys):
                continue
            key = header_keys[column_index]
            if key:
                item[key] = str(value or "").strip()
        row_warnings = [] if missing_required_headers else _normalize_import_item(item, has_new_template=has_new_template)
        row_errors = [] if missing_required_headers else _validate_import_item(item, required_fields=required_fields, has_new_template=has_new_template)
        parsed_rows.append(
            {
                "rowNumber": index,
                "item": item,
                "errors": row_errors,
                "warnings": row_warnings,
            }
        )
        errors.extend(f"Row {index}: {message}" for message in row_errors)
        warnings.extend(f"Row {index}: {message}" for message in row_warnings)

    if not parsed_rows:
        errors.append("File must include at least one item row.")

    return {
        "file_name": filename,
        "file_type": file_type,
        "rows": parsed_rows,
        "errors": errors,
        "warnings": warnings,
    }


def _normalize_import_item(item: dict[str, str], *, has_new_template: bool) -> list[str]:
    warnings = []
    if has_new_template:
        item["item_id"] = item.get("item_id") or _generated_item_id(item)
        item["item_name"] = item.get("item_name") or item.get("employee_name") or item.get("model_no") or "Inventory Item"
        item["category"] = item.get("category") or "IT Equipment"
        item["model"] = item.get("model") or item.get("model_no", "")
        item["serial_number"] = item.get("serial_number") or item.get("serial_no", "")
        item["quantity"] = item.get("quantity") or "1"
        item["unit"] = item.get("unit") or "unit"
        item["condition"] = item.get("condition") or "Good"
        item["assigned_to"] = item.get("assigned_to") or item.get("employee_name", "")
        item["department"] = item.get("department") or ""
        item["minimum_stock_level"] = item.get("minimum_stock_level") or "0"
        if not item.get("status", "").strip():
            item["status"] = "In Use"
        return warnings

    category = item.get("category", "").strip()
    if not category or category not in INVENTORY_CATEGORIES:
        warnings.append(f'Category "{category or "blank"}" defaulted to Other')
        item["category"] = "Other"
    if not item.get("status", "").strip():
        item["status"] = "Available"
    if not item.get("condition", "").strip():
        item["condition"] = "Good"
    if not item.get("unit", "").strip():
        item["unit"] = "pcs"
    if not item.get("minimum_stock_level", "").strip():
        item["minimum_stock_level"] = "0"
    return warnings


def _validate_import_item(item: dict[str, str], *, required_fields: dict[str, str], has_new_template: bool) -> list[str]:
    errors = []
    for key, label in required_fields.items():
        if not str(item.get(key, "")).strip():
            errors.append(f"{label} is required")
    if has_new_template:
        return errors
    if not re.fullmatch(r"\d+", str(item.get("quantity", ""))):
        errors.append("Quantity must be a whole number")
    if not re.fullmatch(r"\d+", str(item.get("minimum_stock_level", ""))):
        errors.append("Minimum stock level must be a whole number")
    for key, label in [("purchase_date", "Purchase date"), ("warranty_end_date", "Warranty end date")]:
        value = str(item.get(key, "")).strip()
        if value and not _is_iso_date(value):
            errors.append(f"{label} must be YYYY-MM-DD")
    return errors


def _generated_item_id(item: dict[str, str]) -> str:
    source = item.get("serial_no") or f'{item.get("employee_name", "")}-{item.get("model_no", "")}' or "inventory-item"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", source.upper()).strip("-")
    return f"INV-{slug or 'ITEM'}"


def _is_iso_date(value: str) -> bool:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    if not match:
        return False
    try:
        date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


def _header_key(header: str) -> str:
    return HEADER_MAP.get(re.sub(r"[^a-z0-9]+", "", str(header).lower()), "")


def _column_index(reference: str) -> int | None:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return None
    index = 0
    for letter in match.group(1):
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _first_by_local_name(root: ElementTree.Element | None, local_name: str) -> ElementTree.Element | None:
    if root is None:
        return None
    for item in root.iter():
        if _local_name(item.tag) == local_name:
            return item
    return None


def _children_by_local_name(root: ElementTree.Element | None, local_name: str) -> list[ElementTree.Element]:
    if root is None:
        return []
    return [item for item in list(root) if _local_name(item.tag) == local_name]


def _local_name(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1]
