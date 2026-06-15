from __future__ import annotations

from flask import jsonify, request, send_file

from tagger.companies_house_client import CompaniesHouseLookupError, lookup_company_profile
from tagger.companies_house_validator import CompaniesHouseValidationError, validate_ixbrl
from tagger.importers import import_csv_text, import_xlsx_bytes
from tagger.ixbrl_generator import build_project_facts, generate_ixbrl
from tagger.models import new_id, utc_now_iso
from tagger.security import MAX_IMPORT_BYTES
from tagger.storage import TaggerStorage
from tagger.template_registry import get_template, list_templates
from tagger.template_service import build_template_payload
from tagger.validation import (
    compare_against_golden_fixture,
    run_arelle_validation,
    run_field_validation,
    run_mandatory_tag_validation,
    run_template_fact_validation,
    validate_generated_xhtml,
)


storage = TaggerStorage()


def _project_or_404(project_id: str):
    project = storage.get_project(project_id)
    if project is None:
        return None, (jsonify({"error": "Project not found"}), 404)
    return project, None


def register_tagger_routes(app):
    @app.route("/api/tagger/templates", methods=["GET"])
    def list_tagger_templates():
        return jsonify({"templates": list_templates()})

    @app.route("/api/tagger/templates/<template_id>", methods=["GET"])
    def get_tagger_template(template_id: str):
        template = get_template(template_id)
        if template is None:
            return jsonify({"error": "Template not found"}), 404
        return jsonify(template)

    @app.route("/api/tagger/companies-house/lookup", methods=["POST"])
    def companies_house_lookup():
        payload = request.get_json(silent=True) or {}
        company_number = payload.get("companyNumber", "")
        project_id = payload.get("projectId")
        try:
            profile = lookup_company_profile(company_number)
            if project_id:
                storage.update_company_snapshot(project_id, profile)
            return jsonify({"profile": profile})
        except CompaniesHouseLookupError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/tagger/projects", methods=["GET", "POST"])
    def tagger_projects():
        if request.method == "GET":
            return jsonify({"projects": storage.list_projects()})
        payload = request.get_json(silent=True) or {}
        project = storage.create_project(payload)
        return jsonify(project.to_dict()), 201

    @app.route("/api/tagger/projects/<project_id>", methods=["GET"])
    def get_tagger_project(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        return jsonify(project.to_dict())

    @app.route("/api/tagger/projects/<project_id>/defaults", methods=["PATCH"])
    def patch_tagger_project_defaults(project_id: str):
        payload = request.get_json(silent=True) or {}
        project = storage.patch_defaults(project_id, payload)
        if project is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project.to_dict())

    @app.route("/api/tagger/projects/<project_id>/load-template", methods=["POST"])
    def load_tagger_template(project_id: str):
        payload = request.get_json(silent=True) or {}
        template_id = payload.get("templateId", "microentity-companies-house-v1")
        template = get_template(template_id)
        if template is None:
            return jsonify({"error": "Template not found"}), 404
        project = storage.set_template(project_id, template_id, template["defaultFilingProfile"])
        if project is None:
            return jsonify({"error": "Project not found"}), 404
        template_payload = build_template_payload(project.to_dict())
        return jsonify({"project": project.to_dict(), "template": template_payload})

    @app.route("/api/tagger/projects/<project_id>/fields/<path:field_id>", methods=["PATCH"])
    def patch_tagger_project_field(project_id: str, field_id: str):
        payload = request.get_json(silent=True) or {}
        project = storage.patch_field(project_id, field_id, payload)
        if project is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project.to_dict())

    @app.route("/api/tagger/projects/<project_id>/import/csv", methods=["POST"])
    def import_tagger_csv(project_id: str):
        payload = request.get_json(silent=True) or {}
        content = payload.get("content", "")
        if not content:
            return jsonify({"error": "CSV content is required"}), 400
        project, error = _project_or_404(project_id)
        if error:
            return error
        encoded_content = content.encode("utf-8")
        if len(encoded_content) > MAX_IMPORT_BYTES:
            return jsonify({"error": "CSV import exceeds the 2MB limit."}), 413
        apply_changes = bool(payload.get("apply", True))
        review = import_csv_text(content, existing_fields=project.fields)
        if apply_changes:
            updated_fields = dict(project.fields)
            updated_fields.update(review["matchedFields"])
            updated = storage.replace_fields(project_id, updated_fields)
        else:
            updated = project
        return jsonify({"review": review, "project": updated.to_dict()})

    @app.route("/api/tagger/projects/<project_id>/import/xlsx", methods=["POST"])
    def import_tagger_xlsx(project_id: str):
        payload = request.get_json(silent=True) or {}
        content_base64 = payload.get("contentBase64", "")
        if not content_base64:
            return jsonify({"error": "XLSX base64 content is required"}), 400
        project, error = _project_or_404(project_id)
        if error:
            return error
        try:
            import base64

            workbook_bytes = base64.b64decode(content_base64)
        except Exception:
            return jsonify({"error": "Invalid XLSX base64 content"}), 400
        if len(workbook_bytes) > MAX_IMPORT_BYTES:
            return jsonify({"error": "XLSX import exceeds the 2MB limit."}), 413
        apply_changes = bool(payload.get("apply", True))
        try:
            review = import_xlsx_bytes(workbook_bytes, existing_fields=project.fields)
        except Exception as exc:
            return jsonify({"error": f"Unable to parse XLSX import: {exc}"}), 400
        if apply_changes:
            updated_fields = dict(project.fields)
            updated_fields.update(review["matchedFields"])
            updated = storage.replace_fields(project_id, updated_fields)
        else:
            updated = project
        return jsonify({"review": review, "project": updated.to_dict()})

    @app.route("/api/tagger/projects/<project_id>/facts", methods=["GET"])
    def get_tagger_facts(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        template = get_template(project.template_id or "microentity-companies-house-v1")
        facts = build_project_facts(project.to_dict(), template)
        storage.save_facts(project_id, facts)
        return jsonify({"facts": list(facts.values())})

    @app.route("/api/tagger/projects/<project_id>/facts/<path:fact_id>", methods=["PATCH"])
    def patch_tagger_fact(project_id: str, fact_id: str):
        payload = request.get_json(silent=True) or {}
        project, error = _project_or_404(project_id)
        if error:
            return error
        facts = dict(project.facts)
        existing_fact = dict(facts.get(fact_id, {}))
        existing_fact.update(payload)
        facts[fact_id] = existing_fact
        updated = storage.save_facts(project_id, facts)
        return jsonify(updated.to_dict())

    @app.route("/api/tagger/projects/<project_id>/preflight", methods=["POST"])
    def preflight_tagger_project(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        template = get_template(project.template_id or "microentity-companies-house-v1")
        facts = build_project_facts(project.to_dict(), template)
        results = (
            run_field_validation(project.to_dict(), template)
            + run_template_fact_validation(project.to_dict(), template, facts)
            + run_mandatory_tag_validation(project.to_dict(), facts)
        )
        status = "pass" if not any(result.get("severity") == "error" for result in results) else "error"
        payload = {"id": new_id("preflight"), "status": status, "results": results, "createdAt": utc_now_iso()}
        storage.add_validation_run(project_id, payload)
        storage.save_facts(project_id, facts)
        return jsonify(payload)

    @app.route("/api/tagger/projects/<project_id>/generate", methods=["POST"])
    def generate_tagger_project(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        template = get_template(project.template_id or "microentity-companies-house-v1")
        generated = generate_ixbrl(project.to_dict(), template)
        export_id = new_id("export")
        export_payload = {
            "id": export_id,
            "createdAt": utc_now_iso(),
            "filename": f"{project_id}-{export_id}.xhtml",
            "factsCount": len(generated["facts"]),
            "hiddenFactsCount": len(
                [fact for fact in generated["facts"].values() if fact.get("visibility") == "hidden"]
            ),
            "contextsCount": len(generated["contexts"]),
            "unitsCount": len(generated["units"]),
            "contextIds": [context.get("id") for context in generated["contexts"]],
            "unitIds": [unit.get("id") for unit in generated["units"]],
        }
        storage.save_facts(project_id, generated["facts"])
        updated = storage.save_export(project_id, export_payload, generated["content"])
        return jsonify(
            {
                "exportId": export_id,
                "content": generated["content"],
                "facts": list(generated["facts"].values()),
                "contexts": generated["contexts"],
                "units": generated["units"],
                "project": updated.to_dict(),
            }
        )

    @app.route("/api/tagger/projects/<project_id>/validate", methods=["POST"])
    def validate_tagger_project(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        template = get_template(project.template_id or "microentity-companies-house-v1")
        generated = generate_ixbrl(project.to_dict(), template)
        field_results = run_field_validation(project.to_dict(), template)
        template_fact_results = run_template_fact_validation(project.to_dict(), template, generated["facts"])
        mandatory = run_mandatory_tag_validation(project.to_dict(), generated["facts"], generated["content"])
        generation = validate_generated_xhtml(generated["content"])
        semantic = compare_against_golden_fixture(generated["content"])
        arelle = run_arelle_validation(generated["content"])
        results = field_results + template_fact_results + mandatory + generation + semantic + arelle
        status = "pass" if not any(result.get("severity") == "error" for result in results) else "error"
        payload = {"id": new_id("validation"), "status": status, "results": results, "createdAt": utc_now_iso()}
        storage.add_validation_run(project_id, payload)
        return jsonify(payload)

    @app.route("/api/tagger/projects/<project_id>/exports/<export_id>", methods=["GET"])
    def download_tagger_export(project_id: str, export_id: str):
        export_path = storage.get_export_path(project_id, export_id)
        if export_path is None or not export_path.exists():
            return jsonify({"error": "Export not found"}), 404
        return send_file(export_path, mimetype="application/xhtml+xml", as_attachment=True, download_name=export_path.name)

    @app.route("/api/tagger/projects/<project_id>/companies-house-result", methods=["POST"])
    def record_companies_house_result(project_id: str):
        payload = request.get_json(silent=True) or {}
        project, error = _project_or_404(project_id)
        if error:
            return error
        project.defaults["companiesHouseResult"] = payload
        if payload.get("status") == "pass":
            project.status = "companies-house-tested"
        storage.save_project(project)
        return jsonify(project.to_dict())

    @app.route("/api/tagger/projects/<project_id>/companies-house-validate", methods=["POST"])
    def validate_with_companies_house(project_id: str):
        project, error = _project_or_404(project_id)
        if error:
            return error
        template = get_template(project.template_id or "microentity-companies-house-v1")
        generated = generate_ixbrl(project.to_dict(), template)
        filename = f"{project_id}-companies-house.xhtml"
        try:
            result = validate_ixbrl(filename, generated["content"])
        except CompaniesHouseValidationError as exc:
            return jsonify({"error": str(exc)}), 502
        project.defaults["companiesHouseResult"] = result
        if result.get("status") == "pass":
            project.status = "companies-house-tested"
        storage.save_project(project)
        return jsonify({"result": result, "project": project.to_dict()})
