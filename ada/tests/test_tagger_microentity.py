import base64
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from routes import tagger_routes
from tagger.companies_house_client import CompaniesHouseLookupError, _normalise_api_key
from tagger.importers import import_csv_text, import_xlsx_bytes
from tagger.ixbrl_generator import build_project_facts, generate_ixbrl, prepare_editable_template_html
from tagger.security import sanitize_html_document
from tagger.storage import TaggerStorage
from tagger.template_registry import get_template
from tagger.validation import (
    compare_against_golden_fixture,
    run_field_validation,
    run_mandatory_tag_validation,
    run_template_fact_validation,
    validate_generated_xhtml,
)


NS = {
    "ix": "http://www.xbrl.org/2013/inlineXBRL",
    "xbrli": "http://www.xbrl.org/2003/instance",
}


def _base_defaults():
    return {
        "company.crn": "10433453",
        "company.name": "Example Filing Ltd",
        "company.addressLine1": "1 Example Street",
        "company.addressLine2": "Example Quarter",
        "company.city": "London",
        "company.region": "Greater London",
        "company.postcode": "E1 1AA",
        "company.principalActivities": "Software development.",
        "project.currentPeriodStart": "2023-11-01",
        "project.currentPeriodEnd": "2024-10-31",
        "project.comparativePeriodStart": "2022-11-01",
        "project.comparativePeriodEnd": "2023-10-31",
        "project.balanceSheetDate": "2024-10-31",
        "project.authorisationDate": "2025-07-31",
        "project.currentPeriodStartDisplay": "01 November 2023",
        "project.currentPeriodEndDisplay": "31 October 2024",
        "project.balanceSheetDateDisplay": "31 October 2024",
        "project.authorisationDateDisplay": "31 July 2025",
        "project.directorName": "Jane Example",
        "project.entityDormant": "false",
        "project.entityTradingStatus": "Trading",
        "project.accountingStandardsApplied": "bus:Micro-entities",
        "project.accountsStatusAuditedOrUnaudited": "bus:AuditExempt-NoAccountantsReport",
        "project.accountsType": "bus:FullAccounts",
        "entity.identifierScheme": "http://www.companieshouse.gov.uk/",
        "entity.identifierValue": "10433453",
    }


def _project_payload():
    return {
        "filingProfile": "companies-house-microentity",
        "defaults": _base_defaults(),
        "fields": {
            "profitLoss.turnover.current": {"rawValue": "18300", "status": "user-edited"},
            "profitLoss.turnover.previous": {"rawValue": "13987", "status": "user-edited"},
            "profitLoss.otherIncome.current": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.otherIncome.previous": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.costMaterials.current": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.costMaterials.previous": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.staffCosts.current": {"rawValue": "(12570)", "status": "user-edited"},
            "profitLoss.staffCosts.previous": {"rawValue": "(12570)", "status": "user-edited"},
            "profitLoss.depreciation.current": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.depreciation.previous": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.otherCharges.current": {"rawValue": "(3723)", "status": "user-edited"},
            "profitLoss.otherCharges.previous": {"rawValue": "(2194)", "status": "user-edited"},
            "profitLoss.tax.current": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.tax.previous": {"rawValue": "0", "status": "user-edited"},
            "profitLoss.profitLoss.current": {"rawValue": "2007", "status": "user-edited"},
            "profitLoss.profitLoss.previous": {"rawValue": "(777)", "status": "user-edited"},
            "balanceSheet.calledUpShareCapital.current": {"rawValue": "1", "status": "user-edited"},
            "balanceSheet.calledUpShareCapital.previous": {"rawValue": "1", "status": "user-edited"},
            "balanceSheet.fixedAssets.current": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.fixedAssets.previous": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.currentAssets.current": {"rawValue": "1000", "status": "user-edited"},
            "balanceSheet.currentAssets.previous": {"rawValue": "1000", "status": "user-edited"},
            "balanceSheet.prepayments.current": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.prepayments.previous": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.creditorsWithinOneYear.current": {"rawValue": "(33294)", "status": "user-edited"},
            "balanceSheet.creditorsWithinOneYear.previous": {"rawValue": "(35301)", "status": "user-edited"},
            "balanceSheet.netCurrentAssets.current": {"rawValue": "(32294)", "status": "user-edited"},
            "balanceSheet.netCurrentAssets.previous": {"rawValue": "(34301)", "status": "user-edited"},
            "balanceSheet.totalAssetsLessCurrentLiabilities.current": {"rawValue": "(32293)", "status": "user-edited"},
            "balanceSheet.totalAssetsLessCurrentLiabilities.previous": {"rawValue": "(34300)", "status": "user-edited"},
            "balanceSheet.creditorsAfterOneYear.current": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.creditorsAfterOneYear.previous": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.provisions.current": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.provisions.previous": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.accruals.current": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.accruals.previous": {"rawValue": "0", "status": "user-edited"},
            "balanceSheet.netAssets.current": {"rawValue": "(32293)", "status": "user-edited"},
            "balanceSheet.netAssets.previous": {"rawValue": "(34300)", "status": "user-edited"},
            "balanceSheet.equity.current": {"rawValue": "(32293)", "status": "user-edited"},
            "balanceSheet.equity.previous": {"rawValue": "(34300)", "status": "user-edited"},
            "notes.averageEmployees.current": {"rawValue": "1", "status": "user-edited"},
            "notes.offBalanceSheetDisclosure": {"rawValue": "No", "status": "user-edited"},
        },
    }


def _build_minimal_xlsx() -> bytes:
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    shared_strings = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
  <si><t>field</t></si>
  <si><t>value</t></si>
  <si><t>turnover current</t></si>
  <si><t>18300</t></si>
</sst>"""
    sheet1 = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>0</v></c>
      <c r="B1" t="s"><v>1</v></c>
    </row>
    <row r="2">
      <c r="A2" t="s"><v>2</v></c>
      <c r="B2" t="s"><v>3</v></c>
    </row>
  </sheetData>
</worksheet>"""
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/sharedStrings.xml", shared_strings)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1)
    return output.getvalue()


class TaggerMicroentityTests(unittest.TestCase):
    def setUp(self):
        self.temp_path = Path(tempfile.mkdtemp(prefix="charles-tagger-tests-"))
        self.storage = TaggerStorage(self.temp_path / "tagger.sqlite3")
        self.original_storage = tagger_routes.storage
        tagger_routes.storage = self.storage
        self.client = app.test_client()

    def tearDown(self):
        tagger_routes.storage = self.original_storage

    def test_template_registry_microentity_exists(self):
        template = get_template("microentity-companies-house-v1")
        self.assertIsNotNone(template)
        self.assertEqual(template["templateId"], "microentity-companies-house-v1")
        self.assertTrue(any(field["fieldId"] == "balanceSheet.fixedAssets.current" for field in template["fields"]))

    def test_prepare_editable_template_html_injects_editable_spans(self):
        html_text = prepare_editable_template_html(_project_payload())
        self.assertIn('data-field-id="profitLoss.turnover.current"', html_text)
        self.assertIn('data-field-state="user-edited"', html_text)
        self.assertIn("Jane Example", html_text)

    def test_sanitize_html_document_removes_scripts_and_event_handlers(self):
        sanitized = sanitize_html_document('<html><body><div onclick="evil()">A</div><script>alert(1)</script></body></html>')
        self.assertNotIn("onclick", sanitized)
        self.assertNotIn("<script", sanitized)

    def test_import_csv_review_reports_overwrites(self):
        review = import_csv_text(
            "field,value\nturnover current,18300\nturnover current,19000\nunknown thing,1",
            existing_fields={"profitLoss.turnover.current": {"rawValue": "17000"}},
        )
        self.assertEqual(review["matchedFields"]["profitLoss.turnover.current"]["rawValue"], "19000")
        self.assertEqual(len(review["overwrittenFields"]), 2)
        self.assertEqual(len(review["warnings"]), 1)
        self.assertEqual(len(review["unmatchedRows"]), 1)

    def test_import_xlsx_bytes_maps_known_fields(self):
        review = import_xlsx_bytes(_build_minimal_xlsx())
        self.assertEqual(review["matchedFields"]["profitLoss.turnover.current"]["rawValue"], "18300")
        self.assertEqual(review["unmatchedRows"], [])

    def test_build_project_facts_includes_hidden_default_facts(self):
        template = get_template("microentity-companies-house-v1")
        facts = build_project_facts(_project_payload(), template)
        self.assertEqual(facts["project.entityDormant"]["qname"], "bus:EntityDormantTruefalse")
        self.assertEqual(facts["project.accountsType"]["qname"], "bus:AccountsType")
        self.assertEqual(facts["project.nameProductionSoftware"]["value"], "UK iXBRL reports by Charles")
        self.assertTrue(facts["profitLoss.profitLoss.previous"]["negative"])
        hidden_qnames = {fact["qname"] for fact in facts.values() if fact.get("visibility") == "hidden"}
        self.assertTrue(
            {
                "bus:NameProductionSoftware",
                "bus:CountryFormationOrIncorporation",
                "bus:PrincipalCurrencyUsedInBusinessReport",
                "bus:LegalFormEntity",
                "bus:AccountingStandardsApplied",
                "bus:AccountsStatusAuditedOrUnaudited",
                "bus:AccountsType",
                "core:DirectorSigningFinancialStatements",
                "bus:EntityDormantTruefalse",
                "bus:EntityTradingStatus",
            }.issubset(hidden_qnames)
        )
        self.assertEqual(
            sum(1 for fact in facts.values() if fact.get("qname") == "core:DirectorSigningFinancialStatements"),
            1,
        )

    def test_field_validation_checks_dates_numbers_and_setup_defaults(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["fields"]["notes.averageEmployees.current"]["rawValue"] = "1.5"
        payload["fields"]["profitLoss.staffCosts.current"]["rawValue"] = "12570"
        payload["defaults"]["project.currentPeriodStart"] = "2024-10-31"
        payload["defaults"]["project.currentPeriodEnd"] = "2023-11-01"
        payload["defaults"]["project.entityDormant"] = "maybe"
        payload["defaults"]["project.defaultCurrency"] = "gbp"
        payload["defaults"]["project.defaultDecimals"] = "two"
        payload["defaults"]["entity.identifierValue"] = "DIFFERENT"
        results = run_field_validation(payload, template)
        self.assertTrue(any("Integer field must not contain decimal places." in result["message"] for result in results))
        self.assertTrue(any("credit-positive sign convention" in result["message"] for result in results))
        self.assertTrue(any("start date must not be after the end date" in result["message"] for result in results))
        self.assertTrue(any("Entity dormant must be true or false." in result["message"] for result in results))
        self.assertTrue(any("three-letter uppercase code" in result["message"] for result in results))
        self.assertTrue(any("Scale and decimals must be whole numbers." in result["message"] for result in results))
        self.assertTrue(any("does not match the entered CRN" in result["message"] for result in results))

    def test_field_validation_requires_confirmation_for_imported_registered_office(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["defaults"]["company.registeredOfficeImportedFromCh"] = "true"
        payload["defaults"]["company.registeredOfficeConfirmed"] = "false"
        results = run_field_validation(payload, template)
        self.assertTrue(any("must be confirmed as still current" in result["message"] for result in results))

    def test_build_project_facts_respects_concept_override(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["fields"]["profitLoss.turnover.current"]["conceptOverrideQname"] = "core:Revenue"
        facts = build_project_facts(payload, template)
        self.assertEqual(facts["profitLoss.turnover.current"]["qname"], "core:Revenue")

    def test_mandatory_tag_validation_flags_missing_registered_number(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["defaults"].pop("company.crn")
        facts = build_project_facts(payload, template)
        results = run_mandatory_tag_validation({"filingProfile": "companies-house-microentity"}, facts)
        self.assertTrue(any(result.get("qname") == "bus:UKCompaniesHouseRegisteredNumber" for result in results))

    def test_mandatory_tag_validation_checks_generated_units_and_duplicates(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        generated = generate_ixbrl(payload, template)
        broken_content = generated["content"].replace('unitRef="pure"', 'unitRef="GBP"', 1)
        duplicate_fragment = '<ix:nonNumeric contextRef="CY" name="bus:EntityDormantTruefalse">false</ix:nonNumeric>'
        broken_content = broken_content.replace("</ix:hidden>", f"{duplicate_fragment}</ix:hidden>", 1)
        results = run_mandatory_tag_validation(payload, generated["facts"], broken_content)
        self.assertTrue(any(result.get("ruleId", "").endswith(".unit") for result in results))
        self.assertTrue(any(result.get("ruleId", "").endswith(".duplicate") for result in results))

    def test_generate_ixbrl_produces_parameterised_semantic_output(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["defaults"]["company.name"] = "Example Filing & Co Ltd"
        generated = generate_ixbrl(payload, template)
        results = validate_generated_xhtml(generated["content"])
        self.assertEqual(results[0]["status"], "pass")
        xml_root = etree.fromstring(generated["content"].encode("utf-8"))
        self.assertEqual(
            xml_root.xpath("count(//ix:hidden/*[@name='bus:EntityDormantTruefalse'])", namespaces=NS),
            1.0,
        )
        self.assertEqual(
            xml_root.xpath("string((//ix:nonNumeric[@name='bus:EntityCurrentLegalOrRegisteredName'])[1])", namespaces=NS),
            "Example Filing & Co Ltd",
        )
        self.assertIn("Example Filing &amp; Co Ltd", generated["content"])
        self.assertEqual(xml_root.xpath("string((//xbrli:identifier)[1])", namespaces=NS), "10433453")
        self.assertEqual(len(generated["contexts"]), len({context["id"] for context in generated["contexts"]}))
        self.assertEqual({unit["id"] for unit in generated["units"]}, {"GBP", "pure"})
        semantic_results = compare_against_golden_fixture(generated["content"])
        self.assertFalse(any(result["severity"] == "error" for result in semantic_results))

    def test_generate_ixbrl_uses_configured_default_currency_in_unit_registry(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["defaults"]["project.defaultCurrency"] = "EUR"
        generated = generate_ixbrl(payload, template)
        self.assertEqual({unit["id"] for unit in generated["units"]}, {"EUR", "pure"})

    def test_generate_ixbrl_applies_default_formats_decimals_and_hidden_currency_fact(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["defaults"]["project.defaultCurrency"] = "EUR"
        payload["defaults"]["project.defaultDecimals"] = "2"
        payload["defaults"]["project.defaultScale"] = "3"
        generated = generate_ixbrl(payload, template)
        xml_root = etree.fromstring(generated["content"].encode("utf-8"))
        turnover = xml_root.xpath("(//ix:nonFraction[@name='core:TurnoverRevenue'])[1]", namespaces=NS)[0]
        self.assertEqual(turnover.attrib.get("decimals"), "2")
        self.assertEqual(turnover.attrib.get("scale"), "3")
        self.assertEqual(turnover.attrib.get("format"), "ixt:num-dot-decimal")
        hidden_currency = xml_root.xpath("string((//ix:hidden/*[@name='bus:PrincipalCurrencyUsedInBusinessReport'])[1])", namespaces=NS)
        self.assertEqual(hidden_currency, "")
        accounting_standards = xml_root.xpath("(//ix:hidden/*[@name='bus:AccountingStandardsApplied'])[1]", namespaces=NS)[0]
        self.assertEqual(accounting_standards.attrib.get("format"), "ixt:fixed-empty")
        production_software = xml_root.xpath("string((//ix:hidden/*[@name='bus:NameProductionSoftware'])[1])", namespaces=NS)
        self.assertEqual(production_software, "UK iXBRL reports by Charles")

    def test_template_fact_validation_flags_missing_required_mapping(self):
        template = get_template("microentity-companies-house-v1")
        payload = _project_payload()
        payload["fields"].pop("profitLoss.turnover.current")
        facts = build_project_facts(payload, template)
        results = run_template_fact_validation(payload, template, facts)
        self.assertTrue(any(result["source"] == "template-facts" and result["severity"] == "error" for result in results))

    def test_tagger_routes_support_preview_apply_xlsx_and_fact_patch(self):
        project = self.client.post("/api/tagger/projects", json={"defaults": _base_defaults()}).get_json()
        project_id = project["id"]
        self.client.post(
            f"/api/tagger/projects/{project_id}/load-template",
            json={"templateId": "microentity-companies-house-v1"},
        )

        workbook_base64 = base64.b64encode(_build_minimal_xlsx()).decode("ascii")
        preview = self.client.post(
            f"/api/tagger/projects/{project_id}/import/xlsx",
            json={"contentBase64": workbook_base64, "apply": False},
        )
        self.assertEqual(preview.status_code, 200)
        preview_body = preview.get_json()
        self.assertIn("profitLoss.turnover.current", preview_body["review"]["matchedFields"])
        project_after_preview = self.client.get(f"/api/tagger/projects/{project_id}").get_json()
        self.assertNotIn("profitLoss.turnover.current", project_after_preview["fields"])

        apply_response = self.client.post(
            f"/api/tagger/projects/{project_id}/import/xlsx",
            json={"contentBase64": workbook_base64, "apply": True},
        )
        self.assertEqual(apply_response.status_code, 200)
        project_after_apply = self.client.get(f"/api/tagger/projects/{project_id}").get_json()
        self.assertEqual(project_after_apply["fields"]["profitLoss.turnover.current"]["rawValue"], "18300")

        patch_fact = self.client.patch(
            f"/api/tagger/projects/{project_id}/facts/custom.fact",
            json={"qname": "core:CustomConcept", "value": "42"},
        )
        self.assertEqual(patch_fact.status_code, 200)
        patched_project = patch_fact.get_json()
        self.assertEqual(patched_project["facts"]["custom.fact"]["value"], "42")

    def test_generate_route_persists_context_and_unit_metadata(self):
        project = self.client.post("/api/tagger/projects", json=_project_payload()).get_json()
        project_id = project["id"]
        self.client.post(
            f"/api/tagger/projects/{project_id}/load-template",
            json={"templateId": "microentity-companies-house-v1"},
        )
        generated = self.client.post(f"/api/tagger/projects/{project_id}/generate")
        self.assertEqual(generated.status_code, 200)
        stored = self.client.get(f"/api/tagger/projects/{project_id}").get_json()
        export_summary = stored["exports"][-1]
        self.assertGreaterEqual(export_summary["contextsCount"], 1)
        self.assertEqual(set(export_summary["unitIds"]), {"GBP", "pure"})

    def test_validation_status_and_company_snapshot_persistence(self):
        project = self.client.post("/api/tagger/projects", json=_project_payload()).get_json()
        project_id = project["id"]
        self.storage.update_company_snapshot(project_id, {"company_name": "Snapshot Ltd", "company_number": "10433453"})
        stored = self.client.get(f"/api/tagger/projects/{project_id}").get_json()
        self.assertEqual(stored["companySnapshot"]["company_name"], "Snapshot Ltd")

        self.client.post(
            f"/api/tagger/projects/{project_id}/load-template",
            json={"templateId": "microentity-companies-house-v1"},
        )
        validation = self.client.post(f"/api/tagger/projects/{project_id}/validate")
        self.assertEqual(validation.status_code, 200)
        validated_project = self.client.get(f"/api/tagger/projects/{project_id}").get_json()
        self.assertEqual(validated_project["status"], "arelle-valid")

    def test_patch_defaults_updates_taxonomy_and_filing_profile(self):
        project = self.client.post("/api/tagger/projects", json={"defaults": _base_defaults()}).get_json()
        project_id = project["id"]
        response = self.client.patch(
            f"/api/tagger/projects/{project_id}/defaults",
            json={
                "taxonomyYear": "2026",
                "taxonomyEntrypoint": "https://xbrl.frc.org.uk/FRS-102/2026-01-01/FRS-102-2026-01-01.xsd",
                "filingProfile": "companies-house-group-audited",
                "project.defaultCurrency": "EUR",
            },
        )
        self.assertEqual(response.status_code, 200)
        updated = response.get_json()
        self.assertEqual(updated["taxonomyYear"], "2026")
        self.assertEqual(updated["filingProfile"], "companies-house-group-audited")
        self.assertEqual(updated["defaults"]["project.defaultCurrency"], "EUR")

    def test_tagger_api_access_hook_rejects_missing_token(self):
        previous = os.environ.get("TAGGER_ACCESS_TOKEN")
        os.environ["TAGGER_ACCESS_TOKEN"] = "secret-token"
        try:
            response = self.client.get("/api/tagger/projects")
            self.assertEqual(response.status_code, 401)
            allowed = self.client.get("/api/tagger/projects", headers={"Authorization": "Bearer secret-token"})
            self.assertEqual(allowed.status_code, 200)
        finally:
            if previous is None:
                os.environ.pop("TAGGER_ACCESS_TOKEN", None)
            else:
                os.environ["TAGGER_ACCESS_TOKEN"] = previous

    def test_companies_house_validation_route_records_pass_result(self):
        project = self.client.post("/api/tagger/projects", json=_project_payload()).get_json()
        project_id = project["id"]
        with patch("routes.tagger_routes.validate_ixbrl") as validate_ixbrl:
            validate_ixbrl.return_value = {
                "status": "pass",
                "fileId": "external-file-id",
                "resultUrl": "https://test-validator.companieshouse.gov.uk/xbrl_validate/result/external-file-id",
                "heading": "Success",
                "message": "Your file is valid.",
            }
            response = self.client.post(f"/api/tagger/projects/{project_id}/companies-house-validate")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["result"]["status"], "pass")
        self.assertEqual(payload["project"]["status"], "companies-house-tested")

    def test_companies_house_api_key_normalisation_trims_quotes_and_whitespace(self):
        self.assertEqual(_normalise_api_key('  "abc123"  '), "abc123")
        self.assertEqual(_normalise_api_key("  'abc123'  "), "abc123")
        self.assertEqual(_normalise_api_key("  abc123  "), "abc123")

    def test_companies_house_api_key_normalisation_rejects_authorization_header_values(self):
        with self.assertRaises(CompaniesHouseLookupError) as exc:
            _normalise_api_key("Basic abc123")
        self.assertIn("raw API key only", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
