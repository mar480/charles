# Tagger Completion Audit

Date audited: 2026-06-12

This branch was audited against `plan.txt` and the requested Companies House-focused micro-entity tagger workflow.

## Product flow evidence

- Tagger-first routing is active in `ada/frontend/src/App.tsx`.
- Project setup, template selection, Companies House lookup, defaults capture, and mandatory status tags are implemented in `ada/frontend/src/components/tagger/ProjectSetupWizard.tsx`.
- Editable template entry, spreadsheet paste, CSV import, XLSX import, fact inspection, taxonomy override, and validation workspace are implemented in `ada/frontend/src/pages/TaggerWorkspace.tsx`.
- Validation review, export summary, Arelle status, and Companies House validation handoff are implemented in `ada/frontend/src/pages/ValidationReview.tsx`.

## Backend evidence

- Tagger routes are registered in `ada/backend/routes/tagger_routes.py`.
- Project persistence is implemented in `ada/backend/tagger/storage.py` using a non-repo local data directory.
- Template registry and fixture-driven mapping are implemented in:
  - `ada/backend/tagger/template_registry.py`
  - `ada/backend/tagger/template_mapping.py`
  - `fixtures/microentity/microentity-fixture-manifest.json`
- iXBRL generation is implemented in `ada/backend/tagger/ixbrl_generator.py`.
- Validation layers are implemented in `ada/backend/tagger/validation.py`.
- Companies House profile lookup proxy is implemented in `ada/backend/tagger/companies_house_client.py`.
- Companies House validator submission and polling integration is implemented in `ada/backend/tagger/companies_house_validator.py`.

## Verification evidence

- Backend tests:
  - `python -m unittest discover -s ada\tests -p test_tagger_microentity.py`
  - Passing on 2026-06-12 with 20 tests.
- Frontend production build:
  - `npm.cmd run build`
  - Passing on 2026-06-12.

## Live external validation evidence

The generated current micro-entity output was submitted programmatically to the Companies House test validator from this environment on 2026-06-12.

Observed result payload:

```json
{
  "status": "pass",
  "fileId": "3a136767-c407-4f9b-8985-949bd32cbf1c",
  "resultUrl": "https://test-validator.companieshouse.gov.uk/xbrl_validate/result/3a136767-c407-4f9b-8985-949bd32cbf1c",
  "heading": "Success Your file is valid",
  "message": "Success Your file is valid Your iXBRL accounts file 'generated.xhtml' meets the iXBRL specification and business validation rules."
}
```

This proves the generated output is accepted by the Companies House test validator for the audited fixture-driven workflow.
