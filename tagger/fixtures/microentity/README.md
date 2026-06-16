# Micro-entity fixture workflow

This fixture provides the first supported golden path for the Companies House tagger.

Files:

- `microentity-untagged.html`: source document loaded into the template workspace.
- `microentity-tagged-valid.xhtml`: semantic golden master used for mapping and output comparison.
- `microentity-fixture-manifest.json`: template metadata, field definitions, and baseline validation assumptions.

## Expected workflow

1. Create a project in the tagger UI.
2. Complete project defaults, including CRN, company name, periods, director, currency, and filing status fields.
3. Load the `microentity-companies-house-v1` template.
4. Enter values directly into the editable template or import a CSV file.
5. Run preflight and mandatory tag validation.
6. Generate iXBRL XHTML.
7. Run Arelle validation in-app.
8. Export the generated XHTML.
9. Submit the export manually to the Companies House test validator and record the result in the app.

## Notes

- The product must parameterise company-specific values from project defaults rather than hard-coding the example company shown in the supplied fixture files.
- Semantic equivalence matters more than byte-for-byte equivalence. Generated output should preserve required facts, periods, units, hidden facts, and validation behaviour.
- CSS in the supplied fixture files should be treated as rendering-stable and left unchanged.
