from __future__ import annotations

from html import escape as html_escape
from typing import Any

from lxml import etree, html

from .context_registry import ContextRegistry
from .fixtures import parse_tagged_tree, parse_untagged_tree
from .template_mapping import TEXT_REPLACEMENTS, VISIBLE_FIELD_BINDINGS
from .unit_registry import UnitRegistry


NS = {
    "xhtml": "http://www.w3.org/1999/xhtml",
    "ix": "http://www.xbrl.org/2013/inlineXBRL",
    "xbrli": "http://www.xbrl.org/2003/instance",
    "xbrldi": "http://xbrl.org/2006/xbrldi",
}

DATE_FORMAT_MAP = {
    "datedaymonthyearen": "ixt:date-day-monthname-year-en",
}

NUMBER_FORMAT_MAP = {
    "numdotdecimal": "ixt:num-dot-decimal",
}

DEFAULT_PRODUCTION_SOFTWARE = "UK iXBRL reports by Charles"


def normalise_numeric(raw_value: Any) -> tuple[str, bool]:
    text = str(raw_value or "").strip().replace(",", "")
    if not text:
        return "0", False
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    return text or "0", negative


def display_value(raw_value: Any) -> str:
    return str(raw_value or "").strip() or ""


def _binding_xpaths(binding: dict[str, Any], key: str) -> list[str]:
    plural_key = f"{key}s"
    if plural_key in binding:
        return [xpath for xpath in binding.get(plural_key, []) if xpath]
    value = binding.get(key)
    return [value] if value else []


def _hidden_format_for_value(qname: str, value: Any) -> str | None:
    text = str(value or "").strip()
    if qname == "bus:EntityDormantTruefalse":
        if text.lower() == "false":
            return "ixt:fixed-false"
        if text.lower() == "true":
            return None
    if not text:
        return "ixt:fixed-empty"
    return None


FIXED_EMPTY_HIDDEN_QNAMES = {
    "bus:CountryFormationOrIncorporation",
    "bus:PrincipalCurrencyUsedInBusinessReport",
    "bus:LegalFormEntity",
    "bus:AccountingStandardsApplied",
    "bus:AccountsStatusAuditedOrUnaudited",
    "bus:AccountsType",
    "core:DirectorSigningFinancialStatements",
    "bus:EntityTradingStatus",
}


def prepare_editable_template_html(project: dict[str, Any]) -> str:
    tree = parse_untagged_tree()
    defaults = project.get("defaults", {})
    fields = project.get("fields", {})

    for field_id, binding in VISIBLE_FIELD_BINDINGS.items():
        xpaths = _binding_xpaths(binding, "untagged_xpath")
        if not xpaths:
            continue
        field_state = fields.get(field_id, {})
        raw_value = field_state.get("rawValue")
        if raw_value in (None, ""):
            raw_value = defaults.get(field_id) or TEXT_REPLACEMENTS.get(field_id, "")
        for xpath in xpaths:
            nodes = tree.xpath(xpath)
            for node in nodes:
                span = html.Element(
                    "span",
                    attrib={
                        "data-field-id": field_id,
                        "data-field-state": field_state.get("status", "empty" if not raw_value else "auto-tagged"),
                        "class": "tagger-editable-field",
                        "contenteditable": "true",
                        "spellcheck": "false",
                    },
                )
                span.text = display_value(raw_value)
                node.clear()
                node.append(span)

    html_text = etree.tostring(tree, encoding="unicode", method="html")
    replacements = {
        TEXT_REPLACEMENTS["company.name"]: defaults.get("company.name", TEXT_REPLACEMENTS["company.name"]),
        TEXT_REPLACEMENTS["company.crn"]: defaults.get("company.crn", TEXT_REPLACEMENTS["company.crn"]),
        TEXT_REPLACEMENTS["project.currentPeriodStart.display"]: defaults.get(
            "project.currentPeriodStartDisplay", TEXT_REPLACEMENTS["project.currentPeriodStart.display"]
        ),
        TEXT_REPLACEMENTS["project.currentPeriodEnd.display"]: defaults.get(
            "project.currentPeriodEndDisplay", TEXT_REPLACEMENTS["project.currentPeriodEnd.display"]
        ),
        TEXT_REPLACEMENTS["project.balanceSheetDate.display"]: defaults.get(
            "project.balanceSheetDateDisplay", TEXT_REPLACEMENTS["project.balanceSheetDate.display"]
        ),
        TEXT_REPLACEMENTS["project.authorisationDate.display"]: defaults.get(
            "project.authorisationDateDisplay", TEXT_REPLACEMENTS["project.authorisationDate.display"]
        ),
        TEXT_REPLACEMENTS["project.directorName"]: defaults.get("project.directorName", TEXT_REPLACEMENTS["project.directorName"]),
    }
    for old, new in replacements.items():
        html_text = html_text.replace(old, html_escape(str(new)))
    return html_text


def build_project_facts(project: dict[str, Any], template: dict[str, Any]) -> dict[str, dict[str, Any]]:
    defaults = project.get("defaults", {})
    fields = project.get("fields", {})
    facts: dict[str, dict[str, Any]] = {}
    default_currency = str(defaults.get("project.defaultCurrency", template.get("defaultCurrency", "GBP")) or "GBP").upper()
    default_decimals = str(defaults.get("project.defaultDecimals", template.get("defaultDecimals", 0)))
    default_scale = str(defaults.get("project.defaultScale", template.get("defaultScale", 0)))
    default_date_format = DATE_FORMAT_MAP.get(
        str(defaults.get("project.defaultDateFormat", "datedaymonthyearen")).strip().lower(),
        "ixt:date-day-monthname-year-en",
    )
    default_number_format = NUMBER_FORMAT_MAP.get(
        str(defaults.get("project.defaultNumberFormat", "numdotdecimal")).strip().lower(),
        "ixt:num-dot-decimal",
    )
    for field in template.get("fields", []):
        field_id = field["fieldId"]
        field_state = fields.get(field_id, {})
        raw_value = field_state.get("rawValue")
        if raw_value in (None, ""):
            raw_value = defaults.get(field_id)
        if raw_value in (None, ""):
            continue
        qname = field_state.get("conceptOverrideQname") or field["concept"]["qname"]
        value = raw_value
        if field["valueType"] in {"monetary", "integer"}:
            value, negative = normalise_numeric(raw_value)
        else:
            negative = False
        facts[field_id] = {
            "fieldId": field_id,
            "qname": qname,
            "value": value,
            "rawValue": raw_value,
            "negative": negative,
            "valueType": field["valueType"],
            "periodRule": field.get("periodRule"),
            "unitRule": field.get("unitRule"),
            "decimals": default_decimals if field["valueType"] in {"monetary", "integer"} else None,
            "scale": default_scale if field["valueType"] in {"monetary", "integer"} else None,
            "format": default_number_format if field["valueType"] in {"monetary", "integer"} else (default_date_format if field["valueType"] == "date" else None),
            "signRule": field.get("signRule"),
            "visibility": field.get("visibility", "visible"),
            "sourceType": field_state.get("sourceType", "project_default" if field_id in defaults else "manual"),
            "conceptOverrideQname": field_state.get("conceptOverrideQname"),
        }
    default_only_facts = {
        "project.nameProductionSoftware": ("bus:NameProductionSoftware", defaults.get("project.productionSoftware", DEFAULT_PRODUCTION_SOFTWARE)),
        "project.countryFormationOrIncorporation": (
            "bus:CountryFormationOrIncorporation",
            "",
        ),
        "project.principalCurrencyUsedInBusinessReport": ("bus:PrincipalCurrencyUsedInBusinessReport", ""),
        "project.legalFormEntity": ("bus:LegalFormEntity", ""),
        "project.entityDormant": ("bus:EntityDormantTruefalse", defaults.get("project.entityDormant")),
        "project.entityTradingStatus": ("bus:EntityTradingStatus", ""),
        "project.accountingStandardsApplied": ("bus:AccountingStandardsApplied", ""),
        "project.accountsStatusAuditedOrUnaudited": ("bus:AccountsStatusAuditedOrUnaudited", ""),
        "project.accountsType": ("bus:AccountsType", ""),
    }
    for field_id, (qname, raw_value) in default_only_facts.items():
        format_value = _hidden_format_for_value(qname, raw_value)
        if raw_value in (None, "") and format_value is None:
            continue
        facts[field_id] = {
            "fieldId": field_id,
            "qname": qname,
            "value": "" if raw_value is None else raw_value,
            "rawValue": "" if raw_value is None else raw_value,
            "negative": False,
            "valueType": "string",
            "periodRule": "current_duration",
            "unitRule": None,
            "decimals": None,
            "scale": None,
            "format": format_value,
            "visibility": "hidden",
            "sourceType": "project_default",
        }
    return facts


def _update_contexts(root, project_defaults: dict[str, Any]) -> None:
    identifier_value = project_defaults.get("company.crn", "10433453")
    identifier_scheme = project_defaults.get("entity.identifierScheme", "http://www.companieshouse.gov.uk/")
    current_start = project_defaults.get("project.currentPeriodStart", "2023-11-01")
    current_end = project_defaults.get("project.currentPeriodEnd", "2024-10-31")
    comparative_start = project_defaults.get("project.comparativePeriodStart", "2022-11-01")
    comparative_end = project_defaults.get("project.comparativePeriodEnd", "2023-10-31")

    for identifier in root.xpath("//xbrli:identifier", namespaces=NS):
        identifier.text = identifier_value
        identifier.attrib["scheme"] = identifier_scheme

    context_updates = {
        "PY": {"startDate": comparative_start, "endDate": comparative_end},
        "CY": {"startDate": current_start, "endDate": current_end},
        "CY_START": {"instant": current_start},
        "CY_END": {"instant": current_end},
        "PY_END": {"instant": comparative_end},
        "Countries_CY": {"startDate": current_start, "endDate": current_end},
        "Currencies_CY": {"startDate": current_start, "endDate": current_end},
        "LegalFormEntity_CY": {"startDate": current_start, "endDate": current_end},
        "AccountingStandards_CY": {"startDate": current_start, "endDate": current_end},
        "AccountsStatus_CY": {"startDate": current_start, "endDate": current_end},
        "AccountsType_CY": {"startDate": current_start, "endDate": current_end},
        "EntityContactInfo_CY": {"startDate": current_start, "endDate": current_end},
        "Director1_CY": {"startDate": current_start, "endDate": current_end},
        "CreditorsWithinOneYear_CY_END": {"instant": current_end},
        "CreditorsWithinOneYear_PY_END": {"instant": comparative_end},
        "CreditorsAfterOneYear_CY_END": {"instant": current_end},
        "CreditorsAfterOneYear_PY_END": {"instant": comparative_end},
    }
    for context_id, values in context_updates.items():
        context_nodes = root.xpath(f"//xbrli:context[@id='{context_id}']", namespaces=NS)
        if not context_nodes:
            continue
        context_node = context_nodes[0]
        for child_name, text in values.items():
            child = context_node.xpath(f".//xbrli:{child_name}", namespaces=NS)
            if child:
                child[0].text = text


def generate_ixbrl(project: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    root = parse_tagged_tree()
    defaults = project.get("defaults", {})
    facts = build_project_facts(project, template)
    default_currency = str(defaults.get("project.defaultCurrency", "GBP") or "GBP").upper()

    context_registry = ContextRegistry()
    unit_registry = UnitRegistry()
    unit_registry.register(default_currency, f"iso4217:{default_currency}")
    unit_registry.register("pure", "xbrli:pure")
    _update_contexts(root, defaults)

    text_fact_defaults = {
        "company.name": defaults.get("company.name", TEXT_REPLACEMENTS["company.name"]),
        "company.crn": defaults.get("company.crn", TEXT_REPLACEMENTS["company.crn"]),
        "company.addressLine1": defaults.get("company.addressLine1", ""),
        "company.addressLine2": defaults.get("company.addressLine2", ""),
        "company.city": defaults.get("company.city", ""),
        "company.region": defaults.get("company.region", ""),
        "company.postcode": defaults.get("company.postcode", ""),
        "company.principalActivities": defaults.get("company.principalActivities", ""),
        "project.currentPeriodStart": defaults.get("project.currentPeriodStartDisplay", TEXT_REPLACEMENTS["project.currentPeriodStart.display"]),
        "project.currentPeriodEnd": defaults.get("project.currentPeriodEndDisplay", TEXT_REPLACEMENTS["project.currentPeriodEnd.display"]),
        "project.balanceSheetDate": defaults.get("project.balanceSheetDateDisplay", TEXT_REPLACEMENTS["project.balanceSheetDate.display"]),
        "project.authorisationDate": defaults.get("project.authorisationDateDisplay", TEXT_REPLACEMENTS["project.authorisationDate.display"]),
    }

    for field_id, binding in VISIBLE_FIELD_BINDINGS.items():
        tagged_xpaths = _binding_xpaths(binding, "tagged_xpath")
        if not tagged_xpaths:
            continue
        for tagged_xpath in tagged_xpaths:
            nodes = root.xpath(tagged_xpath, namespaces=NS)
            if not nodes:
                continue
            node = nodes[0]
            if field_id in facts:
                fact = facts[field_id]
                if fact["valueType"] in {"monetary", "integer"}:
                    node.text = fact["value"]
                    if fact.get("decimals") is not None:
                        node.attrib["decimals"] = str(fact["decimals"])
                    if str(fact.get("scale", "0")) not in {"", "0", "None"}:
                        node.attrib["scale"] = str(fact["scale"])
                    elif "scale" in node.attrib:
                        node.attrib.pop("scale")
                    if fact.get("format"):
                        node.attrib["format"] = str(fact["format"])
                    if fact["negative"]:
                        node.attrib["sign"] = "-"
                    elif "sign" in node.attrib:
                        node.attrib.pop("sign")
                elif fact["valueType"] == "date":
                    node.text = str(text_fact_defaults.get(field_id, fact["rawValue"]))
                    if fact.get("format"):
                        node.attrib["format"] = str(fact["format"])
                else:
                    node.text = str(fact["value"])
            elif field_id in text_fact_defaults:
                node.text = str(text_fact_defaults[field_id])

    hidden_updates = {
        "bus:EntityDormantTruefalse": defaults.get("project.entityDormant", "false"),
        "bus:EntityTradingStatus": "",
        "bus:PrincipalCurrencyUsedInBusinessReport": "",
        "bus:CountryFormationOrIncorporation": "",
        "bus:LegalFormEntity": "",
        "bus:AccountingStandardsApplied": "",
        "bus:AccountsStatusAuditedOrUnaudited": "",
        "bus:AccountsType": "",
        "core:DirectorSigningFinancialStatements": "",
        "bus:NameProductionSoftware": defaults.get("project.productionSoftware", DEFAULT_PRODUCTION_SOFTWARE),
    }
    for qname, value in hidden_updates.items():
        nodes = root.xpath(f"//ix:hidden/*[@name='{qname}']", namespaces=NS)
        for node in nodes:
            text = "" if value is None else str(value)
            node.text = text
            format_value = _hidden_format_for_value(qname, text)
            if format_value:
                node.attrib["format"] = format_value
            elif "format" in node.attrib:
                node.attrib.pop("format")

    visible_director_nodes = root.xpath("//ix:nonNumeric[@name='bus:NameEntityOfficer']", namespaces=NS)
    for node in visible_director_nodes:
        node.text = defaults.get("project.directorName", TEXT_REPLACEMENTS["project.directorName"])

    visible_body_authoriser = root.xpath("//ix:nonNumeric[@name='core:DescriptionBodyAuthorisingFinancialStatements']", namespaces=NS)
    for node in visible_body_authoriser:
        node.text = defaults.get("project.authorisingBody", "the board of directors")

    visible_principal_activity = root.xpath("//ix:nonNumeric[@name='bus:DescriptionPrincipalActivities']", namespaces=NS)
    for node in visible_principal_activity:
        node.text = str(
            facts.get("company.principalActivities", {}).get(
                "rawValue",
                defaults.get("company.principalActivities", ""),
            )
            or "No principal activities supplied."
        )

    visible_address_map = {
        "bus:AddressLine1": facts.get("company.addressLine1", {}).get("rawValue", defaults.get("company.addressLine1", "")),
        "bus:AddressLine2": facts.get("company.addressLine2", {}).get("rawValue", defaults.get("company.addressLine2", "")),
        "bus:PrincipalLocation-CityOrTown": facts.get("company.city", {}).get("rawValue", defaults.get("company.city", "")),
        "bus:CountyRegion": facts.get("company.region", {}).get("rawValue", defaults.get("company.region", "")),
        "bus:PostalCodeZip": facts.get("company.postcode", {}).get("rawValue", defaults.get("company.postcode", "")),
    }
    for qname, value in visible_address_map.items():
        nodes = root.xpath(f"//ix:nonNumeric[@name='{qname}']", namespaces=NS)
        for node in nodes:
            node.text = str(value or "")

    company_name_text = str(
        facts.get("company.name", {}).get("rawValue", defaults.get("company.name", TEXT_REPLACEMENTS["company.name"]))
    )
    for node in root.xpath("//xhtml:div[@class='company-name']", namespaces=NS):
        if len(node):
            continue
        node.text = company_name_text

    period_end_display = str(defaults.get("project.currentPeriodEndDisplay", TEXT_REPLACEMENTS["project.currentPeriodEnd.display"]))
    for node in root.xpath(
        "//xhtml:div[@class='subtitle small' and contains(normalize-space(.), 'for the Period Ended')]",
        namespaces=NS,
    ):
        node.text = f"for the Period Ended {period_end_display}"

    for node in root.xpath(
        "//xhtml:div[@class='center-block small']/xhtml:div[contains(normalize-space(.), 'Unaudited micro entity accounts for the year ended')]",
        namespaces=NS,
    ):
        node.text = f"Unaudited micro entity accounts for the year ended {period_end_display}"

    statement_map = {
        "direp:StatementThatCompanyEntitledToExemptionFromAuditUnderSection477CompaniesAct2006RelatingToSmallCompanies":
            f"For the year ending {period_end_display} the company was entitled to exemption under section 477 of the Companies Act 2006 relating to small companies.",
        "direp:StatementThatMembersHaveNotRequiredCompanyToObtainAnAudit":
            "The members have not required the company to obtain an audit in accordance with section 476 of the Companies Act 2006.",
        "direp:StatementThatDirectorsAcknowledgeTheirResponsibilitiesUnderCompaniesAct":
            "The directors acknowledge their responsibilities for complying with the requirements of the Act with respect to accounting records and the preparation of accounts.",
    }
    for qname, text in statement_map.items():
        nodes = root.xpath(f"//ix:nonNumeric[@name='{qname}']", namespaces=NS)
        for node in nodes:
            node.text = text

    content = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    ).decode("utf-8")

    for context in root.xpath("//xbrli:context", namespaces=NS):
        context_registry.register(context.attrib["id"], {"id": context.attrib["id"]})

    return {
        "content": content,
        "facts": facts,
        "contexts": context_registry.values(),
        "units": unit_registry.values(),
    }
