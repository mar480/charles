from __future__ import annotations

import csv
from io import BytesIO, StringIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET


CSV_FIELD_ALIASES = {
    "turnover current": "profitLoss.turnover.current",
    "turnover previous": "profitLoss.turnover.previous",
    "other income current": "profitLoss.otherIncome.current",
    "other income previous": "profitLoss.otherIncome.previous",
    "profit or loss current": "profitLoss.profitLoss.current",
    "profit or loss previous": "profitLoss.profitLoss.previous",
    "average employees": "notes.averageEmployees.current",
}


XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _normalise_field_key(raw_key: str) -> str:
    return " ".join((raw_key or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _field_alias(raw_key: str) -> str | None:
    return CSV_FIELD_ALIASES.get(_normalise_field_key(raw_key))


def _build_review(rows: list[dict], existing_fields: dict | None = None, source_type: str = "csv_import") -> dict:
    existing_fields = existing_fields or {}
    matched = {}
    unmatched = []
    overwritten = []
    warnings = []

    for row in rows:
        raw_key = (row.get("field") or row.get("label") or "").strip()
        raw_value = (row.get("value") or "").strip()
        if not raw_key:
            unmatched.append({"row": row, "reason": "Missing field/label column"})
            continue
        field_id = _field_alias(raw_key)
        if not field_id:
            unmatched.append({"row": row, "reason": "No template field mapping"})
            continue
        if field_id in matched:
            warnings.append({"fieldId": field_id, "message": "Later import row overwrote an earlier imported value."})
        existing_value = (existing_fields.get(field_id) or {}).get("rawValue")
        if existing_value not in (None, "", raw_value):
            overwritten.append({"fieldId": field_id, "previousValue": existing_value, "incomingValue": raw_value})
        matched[field_id] = {
            "rawValue": raw_value,
            "normalisedValue": raw_value,
            "sourceType": source_type,
            "status": "populated" if raw_value else "empty",
        }

    return {
        "matchedFields": matched,
        "unmatchedRows": unmatched,
        "overwrittenFields": overwritten,
        "warnings": warnings,
    }


def import_csv_text(content: str, existing_fields: dict | None = None) -> dict:
    reader = csv.DictReader(StringIO(content))
    return _build_review(list(reader), existing_fields=existing_fields, source_type="csv_import")


def _load_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("main:si", XLSX_NS):
        parts = []
        for text_node in item.findall(".//main:t", XLSX_NS):
            parts.append(text_node.text or "")
        values.append("".join(parts))
    return values


def _column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return max(value - 1, 0)


def _xlsx_rows_to_dicts(rows: list[list[str]]) -> list[dict]:
    if not rows:
        return []
    headers = [header.strip().lower() for header in rows[0]]
    output = []
    for row in rows[1:]:
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row[index] if index < len(row) else ""
        output.append(record)
    return output


def import_xlsx_bytes(content: bytes, existing_fields: dict | None = None) -> dict:
    with ZipFile(BytesIO(content)) as archive:
        shared_strings = _load_shared_strings(archive)
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = workbook_root.find("main:sheets/main:sheet", XLSX_NS)
        if sheet is None:
            return {
                "matchedFields": {},
                "unmatchedRows": [],
                "overwrittenFields": [],
                "warnings": [{"message": "Workbook did not contain any sheets."}],
            }

        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = None
        relation_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        for relation in workbook_rels.findall("rel:Relationship", XLSX_NS):
            if relation.attrib.get("Id") == relation_id:
                target = relation.attrib.get("Target")
                break
        if not target:
            raise ValueError("Unable to resolve workbook sheet relationship")

        sheet_path = f"xl/{target}"
        sheet_root = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row_node in sheet_root.findall(".//main:sheetData/main:row", XLSX_NS):
            row_values = []
            for cell in row_node.findall("main:c", XLSX_NS):
                index = _column_index_from_ref(cell.attrib.get("r", "A1"))
                while len(row_values) <= index:
                    row_values.append("")
                cell_type = cell.attrib.get("t")
                value_node = cell.find("main:v", XLSX_NS)
                value = value_node.text if value_node is not None and value_node.text is not None else ""
                if cell_type == "s" and value:
                    value = shared_strings[int(value)]
                elif cell_type == "inlineStr":
                    inline = cell.find("main:is/main:t", XLSX_NS)
                    value = inline.text if inline is not None and inline.text is not None else ""
                row_values[index] = value
            rows.append(row_values)

    row_dicts = _xlsx_rows_to_dicts(rows)
    return _build_review(row_dicts, existing_fields=existing_fields, source_type="xlsx_import")
