import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  applyCsvImport,
  generateIxbrl,
  getProject,
  importCsv,
  importXlsx,
  loadTemplate,
  runPreflight,
  updateField,
} from "@/components/tagger/api";
import FactInspector from "@/components/tagger/FactInspector";
import ImportReview from "@/components/tagger/ImportReview";
import MandatoryTagPanel from "@/components/tagger/MandatoryTagPanel";
import TaggerHelpScaffold from "@/components/tagger/TaggerHelpScaffold";
import TemplateCanvas from "@/components/tagger/TemplateCanvas";
import ValidationPanel from "@/components/tagger/ValidationPanel";
import type {
  ConceptChoice,
  ImportReviewData,
  TaggerProject,
  TaggerTemplate,
  ValidationResult,
} from "@/components/tagger/types";
import TaxonomyWorkbenchPanel from "@/components/taxonomy/explorer/TaxonomyWorkbenchPanel";

const TaggerWorkspace = () => {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<TaggerProject | null>(null);
  const [template, setTemplate] = useState<TaggerTemplate | null>(null);
  const [selectedFieldId, setSelectedFieldId] = useState<string>("");
  const [selectedConcept, setSelectedConcept] = useState<ConceptChoice | null>(null);
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
  const [csvContent, setCsvContent] = useState("field,value\nturnover current,18300\nturnover previous,13987\nprofit or loss current,2007\nprofit or loss previous,(777)\naverage employees,1");
  const [xlsxBase64, setXlsxBase64] = useState("");
  const [importReview, setImportReview] = useState<ImportReviewData | null>(null);
  const [status, setStatus] = useState("Loading workspace...");

  const reload = async () => {
    const currentProject = await getProject(id);
    const loaded = await loadTemplate(id, currentProject.templateId || "microentity-companies-house-v1");
    setProject(loaded.project);
    setTemplate(loaded.template);
    setStatus("");
  };

  useEffect(() => {
    void reload().catch((error: Error) => setStatus(error.message));
  }, [id]);

  const selectedField = useMemo(() => template?.fields.find((field) => field.fieldId === selectedFieldId), [selectedFieldId, template]);
  const projectPeriodSummary = `${String(project?.defaults["project.currentPeriodStart"] || "")} to ${String(project?.defaults["project.currentPeriodEnd"] || "")}`;

  const toReviewState = (
    sourceLabel: string,
    review: {
      matchedFields: Record<string, Record<string, unknown>>;
      unmatchedRows: Array<Record<string, unknown>>;
      overwrittenFields: Array<Record<string, unknown>>;
      warnings: Array<Record<string, unknown>>;
    },
  ): ImportReviewData => ({
    sourceLabel,
    matchedCount: Object.keys(review.matchedFields).length,
    unmatchedCount: review.unmatchedRows.length,
    overwrittenCount: review.overwrittenFields.length,
    warningsCount: review.warnings.length,
    matchedFieldIds: Object.keys(review.matchedFields),
    unmatchedRows: review.unmatchedRows,
    overwrittenFields: review.overwrittenFields,
    warnings: review.warnings,
  });

  const handleFieldInput = async (fieldId: string, rawValue: string) => {
    const nextState = {
      rawValue,
      normalisedValue: rawValue,
      sourceType: "manual",
      status: rawValue ? "user-edited" : "empty",
    };
    setProject((current) => current ? ({
      ...current,
      fields: {
        ...current.fields,
        [fieldId]: {
          ...(current.fields[fieldId] || {}),
          ...nextState,
        },
      },
    }) : current);
    await updateField(id, fieldId, nextState);
  };

  const handleBulkFieldInput = async (updates: Array<{ fieldId: string; rawValue: string; sourceType: string }>) => {
    setProject((current) => {
      if (!current) {
        return current;
      }
      const nextFields = { ...current.fields };
      for (const update of updates) {
        nextFields[update.fieldId] = {
          ...(nextFields[update.fieldId] || {}),
          rawValue: update.rawValue,
          normalisedValue: update.rawValue,
          sourceType: update.sourceType,
          status: update.rawValue ? "user-edited" : "empty",
        };
      }
      return {
        ...current,
        fields: nextFields,
      };
    });
    for (const update of updates) {
      await updateField(id, update.fieldId, {
        rawValue: update.rawValue,
        normalisedValue: update.rawValue,
        sourceType: update.sourceType,
        status: update.rawValue ? "user-edited" : "empty",
      });
    }
    await reload();
  };

  const handleApplyConceptOverride = async () => {
    if (!selectedFieldId || !selectedConcept) {
      return;
    }
    await updateField(id, selectedFieldId, {
      conceptOverrideQname: selectedConcept.qname,
      status: "user-confirmed",
      sourceType: "manual",
    });
    await reload();
  };

  const handleClearConceptOverride = async () => {
    if (!selectedFieldId) {
      return;
    }
    await updateField(id, selectedFieldId, {
      conceptOverrideQname: null,
      status: "user-edited",
      sourceType: "manual",
    });
    await reload();
  };

  const handlePreflight = async () => {
    setStatus("Running preflight checks...");
    try {
      const result = await runPreflight(id);
      setValidationResults(result.results);
      setStatus(`Preflight completed with ${result.results.filter((entry) => entry.severity === "error").length} blocking issue(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Preflight failed.");
    }
  };

  const handleGenerate = async () => {
    setStatus("Generating iXBRL export...");
    try {
      await generateIxbrl(id);
      await reload();
      navigate(`/projects/${id}/validate`, { state: { autoGenerateLoaded: true } });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "iXBRL generation failed.");
    }
  };

  const handleImportPreview = async () => {
    const result = await importCsv(id, csvContent);
    setProject(result.project);
    setImportReview(toReviewState("CSV preview", result.review));
  };

  const handleImportApply = async () => {
    const result = await applyCsvImport(id, csvContent);
    setProject(result.project);
    setImportReview(toReviewState("CSV applied", result.review));
    await reload();
  };

  const handleXlsxPreview = async () => {
    if (!xlsxBase64) {
      return;
    }
    const result = await importXlsx(id, xlsxBase64, false);
    setProject(result.project);
    setImportReview(toReviewState("XLSX preview", result.review));
  };

  const handleXlsxApply = async () => {
    if (!xlsxBase64) {
      return;
    }
    const result = await importXlsx(id, xlsxBase64, true);
    setProject(result.project);
    setImportReview(toReviewState("XLSX applied", result.review));
    await reload();
  };

  const handleXlsxFile = async (file: File | null) => {
    if (!file) {
      setXlsxBase64("");
      return;
    }
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    bytes.forEach((value) => {
      binary += String.fromCharCode(value);
    });
    setXlsxBase64(btoa(binary));
  };

  if (!project || !template) {
    return <main className="tagger-page"><p>{status}</p></main>;
  }

  return (
    <main className="tagger-page">
      <section className="tagger-hero">
        <div>
          <div className="tagger-eyebrow">Template workspace</div>
          <h1>{String(project.defaults["company.name"] || "Micro-entity project")}</h1>
          <p className="tagger-muted">{project.id} · {project.status} · {template.label}</p>
          <div className="tagger-actions">
            <span className="tagger-pill">CRN {String(project.defaults["company.crn"] || "unset")}</span>
            <span className="tagger-pill">{projectPeriodSummary}</span>
            <span className="tagger-pill">{Object.keys(project.fields).length} field value(s)</span>
          </div>
        </div>
        <div className="tagger-actions">
          <Link className="tagger-button secondary tagger-button-link" to={`/projects/${id}/setup`}>Back to setup</Link>
          <button type="button" className="tagger-button secondary" onClick={() => void handlePreflight()}>Run preflight</button>
          <button type="button" className="tagger-button primary" onClick={() => void handleGenerate()}>Generate iXBRL</button>
          <Link className="tagger-button secondary tagger-button-link" to={`/projects/${id}/validate`}>Validation review</Link>
        </div>
      </section>
      {status ? (
        <section className="tagger-card">
          <p className="tagger-muted">{status}</p>
        </section>
      ) : null}

      <section className="tagger-layout">
        <div className="tagger-main">
          <div className="tagger-card">
            <h2>Editable micro-entity template</h2>
            <TemplateCanvas
              html={template.editableHtml || ""}
              fieldOrder={template.fields.filter((field) => field.visibility !== "hidden").map((field) => field.fieldId)}
              onFieldInput={(fieldId, rawValue) => void handleFieldInput(fieldId, rawValue)}
              onBulkFieldInput={(updates) => void handleBulkFieldInput(updates)}
              onFieldSelect={setSelectedFieldId}
            />
            <p className="tagger-muted">Paste a row or block from a spreadsheet into the selected template field to fill subsequent mapped fields in template order.</p>
          </div>

          <div className="tagger-card">
            <h2>CSV import into mapped fields</h2>
            <p className="tagger-muted">Preview before applying so the user can inspect matched fields, overwritten values, unmatched rows, and warnings.</p>
            <textarea value={csvContent} onChange={(event) => setCsvContent(event.target.value)} rows={8} />
            <div className="tagger-actions">
              <button type="button" className="tagger-button secondary" onClick={() => void handleImportPreview()}>Preview CSV import</button>
              <button type="button" className="tagger-button secondary" onClick={() => void handleImportApply()}>Apply CSV import</button>
            </div>
          </div>

          <div className="tagger-card">
            <h2>XLSX import into mapped fields</h2>
            <p className="tagger-muted">The first worksheet is read into the template mapping using `field`/`value`-style headers.</p>
            <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => void handleXlsxFile(event.target.files?.[0] || null)} />
            <div className="tagger-actions">
              <button type="button" className="tagger-button secondary" onClick={() => void handleXlsxPreview()} disabled={!xlsxBase64}>Preview XLSX import</button>
              <button type="button" className="tagger-button secondary" onClick={() => void handleXlsxApply()} disabled={!xlsxBase64}>Apply XLSX import</button>
            </div>
          </div>
        </div>

        <aside className="tagger-sidebar">
          <FactInspector
            field={selectedField}
            fieldState={selectedFieldId ? project.fields[selectedFieldId] : undefined}
            selectedConcept={selectedConcept}
            onApplyConceptOverride={handleApplyConceptOverride}
            onClearConceptOverride={handleClearConceptOverride}
          />
          {importReview ? <ImportReview review={importReview} /> : null}
          <MandatoryTagPanel results={validationResults} />
          <ValidationPanel results={validationResults} />
          <TaxonomyWorkbenchPanel
            year={project.taxonomyYear}
            href={project.taxonomyEntrypoint}
            initialQuery={selectedField?.label || ""}
            onConceptChosen={setSelectedConcept}
          />
          <TaggerHelpScaffold />
        </aside>
      </section>
    </main>
  );
};

export default TaggerWorkspace;
