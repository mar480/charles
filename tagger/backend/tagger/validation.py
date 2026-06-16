from __future__ import annotations

import subprocess
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from .fixtures import iter_inline_facts, parse_tagged_tree
from .mandatory_tags import mandatory_rules_for_profile


UNESCAPED_AMPERSAND_RE = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")


def _parse_date(raw_value: str) -> bool:
    try:
        datetime.strptime(raw_value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _parse_numeric(raw_value: str) -> tuple[bool, bool, bool]:
    text = str(raw_value or "").strip().replace(",", "")
    if not text:
        return False, False, False
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if text in {"", "-"}:
        return False, negative, False
    if text.count(".") > 1:
        return False, negative, False
    integer_like = "." not in text
    try:
        float(text)
        return True, negative, integer_like
    except ValueError:
        return False, negative, integer_like


def _normalise_person_name(raw_value: str) -> str:
    text = " ".join(str(raw_value or "").strip().split())
    if not text:
        return ""
    if "," in text:
        last_name, first_names = [part.strip() for part in text.split(",", 1)]
        text = f"{first_names} {last_name}".strip()
    parts = [part for part in re.split(r"\s+", text.lower()) if part]
    return " ".join(parts)


def run_field_validation(project: dict[str, Any], template: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    results = []
    defaults = project.get("defaults") or {}
    fields = project.get("fields") or {}
    template_fields = template.get("fields", []) if template else []

    def effective_value(field_id: str) -> str:
        field_state = fields.get(field_id, {})
        raw_value = field_state.get("rawValue")
        if raw_value in (None, ""):
            raw_value = defaults.get(field_id, "")
        return str(raw_value or "").strip()

    for field in template_fields:
        field_id = field["fieldId"]
        field_state = fields.get(field_id, {})
        raw_value = field_state.get("rawValue")
        if raw_value in (None, ""):
            raw_value = defaults.get(field_id, "")
        raw_text = str(raw_value or "").strip()
        if field.get("required") and not raw_text:
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "field-validation",
                    "relatedFieldId": field_id,
                    "message": "Required field is empty.",
                }
            )
            continue
        if not raw_text:
            continue
        value_type = field.get("valueType")
        if value_type in {"monetary", "integer"}:
            valid_numeric, negative, integer_like = _parse_numeric(raw_text)
            if not valid_numeric:
                results.append(
                    {
                        "status": "error",
                        "severity": "error",
                        "source": "field-validation",
                        "relatedFieldId": field_id,
                        "message": "Numeric field contains an invalid value.",
                    }
                )
            elif value_type == "integer" and not integer_like:
                results.append(
                    {
                        "status": "error",
                        "severity": "error",
                        "source": "field-validation",
                        "relatedFieldId": field_id,
                        "message": "Integer field must not contain decimal places.",
                    }
                )
            elif field_id == "notes.averageEmployees.current" and valid_numeric and float(text := raw_text.strip().replace(",", "").replace("(", "-").replace(")", "")) < 0:
                results.append(
                    {
                        "status": "error",
                        "severity": "error",
                        "source": "field-validation",
                        "relatedFieldId": field_id,
                        "message": "Average number of employees must not be less than 0.",
                    }
                )
        elif value_type == "date" and not _parse_date(raw_text):
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "field-validation",
                    "relatedFieldId": field_id,
                    "message": "Date field must use YYYY-MM-DD format.",
                }
            )

    if defaults.get("project.entityDormant") not in (None, "", "true", "false"):
        results.append(
            {
                "status": "error",
                "severity": "error",
                "source": "field-validation",
                "relatedFieldId": "project.entityDormant",
                "message": "Entity dormant must be true or false.",
            }
        )
    default_currency = str(defaults.get("project.defaultCurrency", "")).strip()
    if default_currency and (len(default_currency) != 3 or not default_currency.isalpha() or default_currency.upper() != default_currency):
        results.append(
            {
                "status": "error",
                "severity": "error",
                "source": "field-validation",
                "relatedFieldId": "project.defaultCurrency",
                "message": "Default currency must be a three-letter uppercase code.",
            }
        )
    for field_id in ("project.defaultScale", "project.defaultDecimals"):
        raw_value = str(defaults.get(field_id, "")).strip()
        if raw_value and not raw_value.lstrip("-").isdigit():
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "field-validation",
                    "relatedFieldId": field_id,
                    "message": "Scale and decimals must be whole numbers.",
                }
            )
    date_pairs = [
        ("project.currentPeriodStart", "project.currentPeriodEnd", "Current reporting period"),
        ("project.comparativePeriodStart", "project.comparativePeriodEnd", "Comparative reporting period"),
    ]
    for start_key, end_key, label in date_pairs:
        start_value = str(defaults.get(start_key, "")).strip()
        end_value = str(defaults.get(end_key, "")).strip()
        if start_value and end_value and _parse_date(start_value) and _parse_date(end_value) and start_value > end_value:
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "field-validation",
                    "relatedFieldId": start_key,
                    "message": f"{label} start date must not be after the end date.",
                }
            )
    identifier_value = str(defaults.get("entity.identifierValue", "")).strip()
    company_crn = str(defaults.get("company.crn", "")).strip()
    if identifier_value and company_crn and identifier_value != company_crn:
        results.append(
            {
                "status": "warning",
                "severity": "warning",
                "source": "field-validation",
                "relatedFieldId": "entity.identifierValue",
                "message": "Entity identifier value does not match the entered CRN.",
            }
        )
    if str(defaults.get("company.registeredOfficeImportedFromCh", "")).lower() == "true" and str(
        defaults.get("company.registeredOfficeConfirmed", "")
    ).lower() != "true":
        results.append(
            {
                "status": "error",
                "severity": "error",
                "source": "field-validation",
                "relatedFieldId": "company.registeredOfficeConfirmed",
                "message": "Registered office imported from Companies House must be confirmed as still current before filing.",
            }
        )

    company_snapshot = project.get("companySnapshot") or {}
    snapshot_number = str(company_snapshot.get("company_number", "")).strip()
    if company_crn and snapshot_number and company_crn != snapshot_number:
        results.append(
            {
                "status": "error",
                "severity": "error",
                "source": "field-validation",
                "relatedFieldId": "company.crn",
                "message": "Entered CRN does not match the saved Companies House snapshot.",
            }
        )
    snapshot_name = str(company_snapshot.get("company_name", "")).strip()
    company_name = effective_value("company.name")
    if company_name and snapshot_name and company_name != snapshot_name:
        results.append(
            {
                "status": "warning",
                "severity": "warning",
                "source": "field-validation",
                "relatedFieldId": "company.name",
                "message": "Company name differs from the saved Companies House snapshot.",
            }
        )
    director_name = effective_value("project.directorName")
    snapshot_directors = [
        str(name).strip()
        for name in company_snapshot.get("director_names", [])
        if str(name).strip()
    ]
    normalised_director_name = _normalise_person_name(director_name)
    normalised_snapshot_directors = {_normalise_person_name(name) for name in snapshot_directors}
    if director_name and snapshot_directors and normalised_director_name not in normalised_snapshot_directors:
        results.append(
            {
                "status": "warning",
                "severity": "warning",
                "source": "field-validation",
                "relatedFieldId": "project.directorName",
                "message": (
                    f"Director signing financial statements '{director_name}' does not match the current directors "
                    f"in the saved Companies House snapshot: {', '.join(snapshot_directors)}."
                ),
            }
        )
    snapshot_address = company_snapshot.get("registered_office_address") or {}
    address_checks = [
        ("company.addressLine1", "address_line_1", "Address line 1"),
        ("company.addressLine2", "address_line_2", "Address line 2"),
        ("company.city", "locality", "City or town"),
        ("company.region", "region", "Region"),
        ("company.postcode", "postal_code", "Postcode"),
    ]
    for field_id, snapshot_key, label in address_checks:
        current_value = effective_value(field_id)
        snapshot_value = str(snapshot_address.get(snapshot_key, "")).strip()
        if current_value and snapshot_value and current_value != snapshot_value:
            results.append(
                {
                    "status": "warning",
                    "severity": "warning",
                    "source": "field-validation",
                    "relatedFieldId": field_id,
                    "message": f"{label} differs from the saved Companies House registered office snapshot.",
                }
            )

    for field_id, field_state in fields.items():
        if field_state.get("rawValue") and field_state.get("status") == "error":
            results.append(
                {
                    "status": "warning",
                    "severity": "warning",
                    "source": "field-validation",
                    "relatedFieldId": field_id,
                    "message": "Field is populated but still marked as error.",
                }
            )
    if not results:
        results.append(
            {
                "status": "pass",
                "severity": "info",
                "source": "field-validation",
                "message": "Field validation passed.",
            }
        )
    return results


def run_template_fact_validation(project: dict[str, Any], template: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    facts_by_field = facts or {}
    for field in template.get("fields", []):
        field_id = field["fieldId"]
        fact = facts_by_field.get(field_id)
        if field.get("required") and fact is None:
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "template-facts",
                    "relatedFieldId": field_id,
                    "message": f"Required mapped field '{field['label']}' is missing.",
                }
            )
            continue
        if fact is None:
            continue
        if not fact.get("qname") or ":" not in str(fact.get("qname")):
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "template-facts",
                    "relatedFieldId": field_id,
                    "message": f"Field '{field['label']}' does not resolve to a valid prefixed QName.",
                }
            )
        if field.get("unitRule") and not fact.get("unitRule"):
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "template-facts",
                    "relatedFieldId": field_id,
                    "message": f"Field '{field['label']}' is missing its unit rule.",
                }
            )
        if field.get("periodRule") and not fact.get("periodRule"):
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "template-facts",
                    "relatedFieldId": field_id,
                    "message": f"Field '{field['label']}' is missing its period rule.",
                }
            )
        if fact.get("valueType") in {"monetary", "integer"} and str(fact.get("value", "")).strip() == "":
            results.append(
                {
                    "status": "error",
                    "severity": "error",
                    "source": "template-facts",
                    "relatedFieldId": field_id,
                    "message": f"Field '{field['label']}' has no normalised numeric value.",
                }
            )
    if not results:
        results.append(
            {
                "status": "pass",
                "severity": "info",
                "source": "template-facts",
                "message": "Template fact validation passed.",
            }
        )
    return results


def _context_periods(root) -> dict[str, dict[str, str]]:
    contexts = {}
    for context in root.xpath("//xbrli:context", namespaces={"xbrli": "http://www.xbrl.org/2003/instance"}):
        period = context.find("{http://www.xbrl.org/2003/instance}period")
        if period is None:
            continue
        instant = period.findtext("{http://www.xbrl.org/2003/instance}instant")
        start_date = period.findtext("{http://www.xbrl.org/2003/instance}startDate")
        end_date = period.findtext("{http://www.xbrl.org/2003/instance}endDate")
        if instant:
            contexts[context.attrib.get("id", "")] = {"periodType": "instant", "instant": instant}
        elif start_date and end_date:
            contexts[context.attrib.get("id", "")] = {
                "periodType": "duration",
                "startDate": start_date,
                "endDate": end_date,
            }
    return contexts


def _generated_fact_details(content: str) -> list[dict[str, Any]]:
    root = etree.fromstring(content.encode("utf-8"))
    details = []
    hidden_facts = root.xpath("//ix:hidden/*", namespaces={"ix": "http://www.xbrl.org/2013/inlineXBRL"})
    visible_facts = root.xpath("//ix:nonFraction | //ix:nonNumeric", namespaces={"ix": "http://www.xbrl.org/2013/inlineXBRL"})
    for fact in hidden_facts:
        details.append(
            {
                "name": fact.attrib.get("name", ""),
                "contextRef": fact.attrib.get("contextRef", ""),
                "unitRef": fact.attrib.get("unitRef"),
                "decimals": fact.attrib.get("decimals"),
                "visibility": "hidden",
                "value": "".join(fact.itertext()).strip(),
            }
        )
    for fact in visible_facts:
        details.append(
            {
                "name": fact.attrib.get("name", ""),
                "contextRef": fact.attrib.get("contextRef", ""),
                "unitRef": fact.attrib.get("unitRef"),
                "decimals": fact.attrib.get("decimals"),
                "visibility": "visible",
                "value": "".join(fact.itertext()).strip(),
            }
        )
    return details


def _expected_unit_id(rule: dict[str, Any], project: dict[str, Any]) -> str | None:
    expected = rule.get("expected_unit")
    if expected == "default_currency":
        return str((project.get("defaults") or {}).get("project.defaultCurrency", "GBP")).upper()
    return expected


def _period_matches(rule: dict[str, Any], detail: dict[str, Any], context_map: dict[str, dict[str, str]], project: dict[str, Any]) -> bool:
    context = context_map.get(detail.get("contextRef", ""))
    if context is None:
        return False
    expected_period = rule.get("expected_period")
    if expected_period == "instant" and context.get("periodType") != "instant":
        return False
    if expected_period == "duration" and context.get("periodType") != "duration":
        return False
    expected_context = rule.get("expected_context")
    defaults = project.get("defaults") or {}
    if expected_context == "balance_sheet_date":
        return context.get("instant") == str(defaults.get("project.balanceSheetDate", ""))
    if expected_context == "reporting_period":
        qname = rule.get("qname")
        if qname == "bus:StartDateForPeriodCoveredByReport":
            return context.get("instant") == str(defaults.get("project.currentPeriodStart", ""))
        if qname == "bus:EndDateForPeriodCoveredByReport":
            return context.get("instant") == str(defaults.get("project.currentPeriodEnd", ""))
        return (
            context.get("startDate") == str(defaults.get("project.currentPeriodStart", ""))
            and context.get("endDate") == str(defaults.get("project.currentPeriodEnd", ""))
        )
    return True


def _namespace_prefix_resolves(qname: str, generated_content: str) -> bool:
    if ":" not in qname:
        return False
    prefix = qname.split(":", 1)[0]
    root = etree.fromstring(generated_content.encode("utf-8"))
    return prefix in (root.nsmap or {})


def run_mandatory_tag_validation(
    project: dict[str, Any],
    facts: dict[str, Any],
    generated_content: str | None = None,
) -> list[dict[str, Any]]:
    results = []
    profile = project.get("filingProfile", "companies-house-microentity")
    facts_by_qname = {}
    for fact in facts.values():
        facts_by_qname.setdefault(fact.get("qname"), []).append(fact)
    generated_details = _generated_fact_details(generated_content) if generated_content else []
    details_by_qname: dict[str, list[dict[str, Any]]] = {}
    for detail in generated_details:
        details_by_qname.setdefault(detail["name"], []).append(detail)
    context_map = etree.fromstring(generated_content.encode("utf-8")) if generated_content else None
    context_periods = _context_periods(context_map) if context_map is not None else {}

    for rule in mandatory_rules_for_profile(profile):
        matching = facts_by_qname.get(rule["qname"], [])
        if not matching:
            results.append(
                {
                    "status": "error",
                    "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}",
                    "qname": rule["qname"],
                    "message": f"{rule['label']} is missing.",
                    "severity": "error",
                    "source": "mandatory-tags",
                    "relatedFieldId": rule.get("relatedFieldId"),
                }
            )
            continue
        if not all(fact.get("sourceType") for fact in matching):
            results.append(
                {
                    "status": "error",
                    "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.source",
                    "qname": rule["qname"],
                    "message": f"{rule['label']} does not have a traceable fact source.",
                    "severity": "error",
                    "source": "mandatory-tags",
                    "relatedFieldId": rule.get("relatedFieldId"),
                }
            )
        if rule["validation"]["non_empty"]:
            if not any(str(fact.get("value", "")).strip() for fact in matching):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} is empty.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
        if generated_content:
            generated_matches = details_by_qname.get(rule["qname"], [])
            if not generated_matches:
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.generated",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} is not present in the generated iXBRL output.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
                continue
            signatures = {
                (
                    item.get("contextRef"),
                    item.get("unitRef"),
                    item.get("decimals"),
                    item.get("visibility"),
                    item.get("value"),
                )
                for item in generated_matches
            }
            if len(signatures) != len(generated_matches):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.duplicate",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} is duplicated in the generated output.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
            expected_unit_id = _expected_unit_id(rule, project)
            if expected_unit_id and not any(item.get("unitRef") == expected_unit_id for item in generated_matches):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.unit",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} does not use the expected unit {expected_unit_id}.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
            if not any(_period_matches(rule, item, context_periods, project) for item in generated_matches):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.context",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} does not use an expected reporting context.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
            if rule.get("usually_hidden") and not any(item.get("visibility") == "hidden" for item in generated_matches):
                results.append(
                    {
                        "status": "warning",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.visibility",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} is usually hidden but appears visibly in the generated output.",
                        "severity": "warning",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
            if not _namespace_prefix_resolves(rule["qname"], generated_content):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}.namespace",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} uses a QName prefix that is not declared in the generated document.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )
        allowed_values = rule["validation"].get("allowed_values") or []
        if allowed_values:
            values = {str(fact.get("value")).lower() for fact in matching}
            if values.isdisjoint({value.lower() for value in allowed_values}):
                results.append(
                    {
                        "status": "error",
                        "ruleId": f"mandatory.{rule['qname'].replace(':', '.')}",
                        "qname": rule["qname"],
                        "message": f"{rule['label']} has an invalid value.",
                        "severity": "error",
                        "source": "mandatory-tags",
                        "relatedFieldId": rule.get("relatedFieldId"),
                    }
                )

    if not results:
        results.append(
            {
                "status": "pass",
                "severity": "info",
                "source": "mandatory-tags",
                "message": "Mandatory tag checks passed.",
            }
        )

    return results


def validate_generated_xhtml(content: str) -> list[dict[str, Any]]:
    if UNESCAPED_AMPERSAND_RE.search(content):
        return [
            {
                "status": "error",
                "severity": "error",
                "source": "generation",
                "message": "Generated XHTML contains an unescaped '&' character.",
            }
        ]
    try:
        etree.fromstring(content.encode("utf-8"))
        return [{"status": "pass", "severity": "info", "source": "generation", "message": "Generated XHTML is well-formed XML."}]
    except etree.XMLSyntaxError as exc:
        return [{"status": "error", "severity": "error", "source": "generation", "message": str(exc)}]


def _fact_signature(fact) -> tuple[str, str, str, str | None, str | None]:
    return (
        etree.QName(fact).localname,
        fact.attrib.get("name", ""),
        fact.attrib.get("contextRef", ""),
        fact.attrib.get("unitRef"),
        fact.attrib.get("decimals"),
    )


def compare_against_golden_fixture(generated_content: str) -> list[dict[str, Any]]:
    generated_root = etree.fromstring(generated_content.encode("utf-8"))
    golden_root = parse_tagged_tree()
    generated_signatures = {_fact_signature(fact) for fact in iter_inline_facts(generated_root)}
    golden_signatures = {_fact_signature(fact) for fact in iter_inline_facts(golden_root)}

    missing = golden_signatures - generated_signatures
    extra = generated_signatures - golden_signatures
    results = []

    for signature in sorted(missing):
        results.append(
            {
                "status": "error",
                "severity": "error",
                "source": "golden-fixture",
                "qname": signature[1],
                "message": f"Generated output is missing golden fixture fact {signature[1]} in context {signature[2]}.",
            }
        )
    for signature in sorted(extra):
        results.append(
            {
                "status": "warning",
                "severity": "warning",
                "source": "golden-fixture",
                "qname": signature[1],
                "message": f"Generated output contains additional fact {signature[1]} in context {signature[2]}.",
            }
        )
    if not results:
        results.append(
            {
                "status": "pass",
                "severity": "info",
                "source": "golden-fixture",
                "message": "Generated output matches the golden fixture semantically at the inline fact signature level.",
            }
        )
    return results


def run_arelle_validation(content: str) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        xhtml_path = Path(tmp_dir) / "document.xhtml"
        log_path = Path(tmp_dir) / "arelle-log.txt"
        xhtml_path.write_text(content, encoding="utf-8")
        command = [
            "python",
            "-m",
            "arelle.CntlrCmdLine",
            "--file",
            str(xhtml_path),
            "--validate",
            "--logFile",
            str(log_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except Exception as exc:
            return [
                {
                    "status": "warning",
                    "severity": "warning",
                    "source": "arelle",
                    "message": f"Arelle could not be executed locally: {exc}",
                }
            ]

        log_text = ""
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="ignore")
        elif completed.stdout:
            log_text = completed.stdout
        elif completed.stderr:
            log_text = completed.stderr

        log_text = log_text.strip() or completed.stderr.strip() or completed.stdout.strip()
        lower_log = log_text.lower()
        if completed.returncode != 0 or "error" in lower_log:
            severity = "error"
            status = "error"
        elif "warning" in lower_log:
            severity = "warning"
            status = "warning"
        else:
            severity = "info"
            status = "pass"

        return [
            {
                "status": status,
                "severity": severity,
                "source": "arelle",
                "message": log_text or "Arelle validation completed.",
            }
        ]
