import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  generateIxbrl,
  getProject,
  recordCompaniesHouseResult,
  runCompaniesHouseValidation,
  runValidation,
} from "@/components/tagger/api";
import ExportPanel from "@/components/tagger/ExportPanel";
import MandatoryTagPanel from "@/components/tagger/MandatoryTagPanel";
import ValidationPanel from "@/components/tagger/ValidationPanel";
import type { CompaniesHouseValidationResult, TaggerExportSummary, TaggerProject, ValidationResult } from "@/components/tagger/types";

const ValidationReview = () => {
  const { id = "" } = useParams();
  const location = useLocation();
  const [project, setProject] = useState<TaggerProject | null>(null);
  const [results, setResults] = useState<ValidationResult[]>([]);
  const [exportSummary, setExportSummary] = useState<{
    exportId: string;
    factsCount: number;
    hiddenFactsCount: number;
    contextsCount: number;
    unitsCount: number;
    contextIds: string[];
    unitIds: string[];
    content: string;
  } | null>(null);
  const [companyHouseStatus, setCompanyHouseStatus] = useState("pending");
  const [companyHouseNotes, setCompanyHouseNotes] = useState("");
  const [companyHouseResult, setCompanyHouseResult] = useState<CompaniesHouseValidationResult | null>(null);
  const [status, setStatus] = useState("Loading validation review...");
  const blockingIssues = results.filter((result) => result.severity === "error").length;
  const warningIssues = results.filter((result) => result.severity === "warning").length;
  const exports = Array.isArray(project?.exports) ? project.exports : [];
  const latestExport = (exports.length ? exports[exports.length - 1] : null) as TaggerExportSummary | null;

  useEffect(() => {
    void getProject(id)
      .then(async (nextProject) => {
        setProject(nextProject);
        const savedValidation = Array.isArray(nextProject.validationRuns) && nextProject.validationRuns.length
          ? nextProject.validationRuns[nextProject.validationRuns.length - 1]
          : null;
        setResults(Array.isArray(savedValidation?.results) ? (savedValidation?.results as ValidationResult[]) : []);
        const savedExport = Array.isArray(nextProject.exports) && nextProject.exports.length
          ? (nextProject.exports[nextProject.exports.length - 1] as TaggerExportSummary)
          : undefined;
        if (savedExport) {
          setExportSummary({
            exportId: savedExport.id,
            factsCount: Number(savedExport.factsCount || 0),
            hiddenFactsCount: Number(savedExport.hiddenFactsCount || 0),
            contextsCount: Number(savedExport.contextsCount || 0),
            unitsCount: Number(savedExport.unitsCount || 0),
            contextIds: savedExport.contextIds || [],
            unitIds: savedExport.unitIds || [],
            content: "",
          });
        }
        const savedResult = (nextProject.defaults["companiesHouseResult"] as Record<string, unknown> | undefined) || {};
        setCompanyHouseStatus(String(savedResult.status || "pending"));
        setCompanyHouseNotes(String(savedResult.notes || savedResult.feedback || ""));
        if (savedResult.status && savedResult.fileId && savedResult.resultUrl) {
          setCompanyHouseResult({
            status: String(savedResult.status),
            fileId: String(savedResult.fileId),
            resultUrl: String(savedResult.resultUrl),
            heading: String(savedResult.heading || ""),
            message: String(savedResult.message || ""),
          });
        }
        if ((!savedValidation || !Array.isArray(savedValidation.results) || savedValidation.results.length === 0) && location.state == null) {
          const validation = await runValidation(id);
          setResults(validation.results);
        }
        setStatus("");
      })
      .catch((error: Error) => setStatus(error.message));
  }, [id, location.state]);

  const handleValidate = async () => {
    setStatus("Running full validation...");
    try {
      const validation = await runValidation(id);
      setResults(validation.results);
      setStatus(`Validation completed with ${validation.results.filter((entry) => entry.severity === "error").length} blocking issue(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Validation failed.");
    }
  };

  const handleGenerate = async () => {
    setStatus("Generating export...");
    try {
      const generated = await generateIxbrl(id);
      setProject(generated.project);
      setExportSummary({
        exportId: generated.exportId,
        factsCount: generated.facts.length,
        hiddenFactsCount: generated.facts.filter((fact) => fact.visibility === "hidden").length,
        contextsCount: generated.contexts.length,
        unitsCount: generated.units.length,
        contextIds: generated.contexts.map((context) => String(context.id || "")),
        unitIds: generated.units.map((unit) => String(unit.id || "")),
        content: generated.content,
      });
      setStatus("Export generated.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Export generation failed.");
    }
  };

  const handleRecord = async () => {
    setStatus("Recording Companies House result...");
    try {
      const updated = await recordCompaniesHouseResult(id, { status: companyHouseStatus, notes: companyHouseNotes, feedback: companyHouseNotes });
      setProject(updated);
      setStatus("Companies House result recorded.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to record Companies House result.");
    }
  };

  const handleCompaniesHouseValidation = async () => {
    setStatus("Submitting export to the Companies House validator...");
    try {
      const response = await runCompaniesHouseValidation(id);
      setProject(response.project);
      setCompanyHouseResult(response.result);
      setCompanyHouseStatus(response.result.status);
      setCompanyHouseNotes(response.result.message);
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Companies House validation failed.");
    }
  };

  const handleFeedbackFile = async (file: File | null) => {
    if (!file) {
      return;
    }
    const text = await file.text();
    setCompanyHouseNotes(text);
  };

  if (!project) {
    return <main className="tagger-page"><p>{status}</p></main>;
  }

  return (
    <main className="tagger-page">
      <section className="tagger-hero">
        <div>
          <div className="tagger-eyebrow">Validation review</div>
          <h1>{String(project.defaults["company.name"] || "Project")}</h1>
          <p className="tagger-muted">Mandatory tags, generated XHTML checks, Arelle output, and Companies House test-validator record.</p>
          <div className="tagger-actions">
            <span className="tagger-pill">{blockingIssues} blocking issue(s)</span>
            <span className="tagger-pill">{warningIssues} warning(s)</span>
            <span className="tagger-pill">{project.status}</span>
          </div>
        </div>
        <div className="tagger-actions">
          <Link className="tagger-button secondary tagger-button-link" to={`/projects/${id}/tag`}>Back to workspace</Link>
          <button type="button" className="tagger-button secondary" onClick={() => void handleValidate()}>Run validation</button>
          <button type="button" className="tagger-button primary" onClick={() => void handleGenerate()}>Generate export</button>
        </div>
      </section>
      {status ? (
        <section className="tagger-card">
          <p className="tagger-muted">{status}</p>
        </section>
      ) : null}

      <section className="tagger-layout">
        <div className="tagger-main">
          <MandatoryTagPanel results={results} />
          <ValidationPanel results={results} />
          <div className="tagger-card">
            <h3>Companies House test validator record</h3>
            <p className="tagger-muted">Download the generated XHTML, submit it manually to the Companies House test validator, then record the result here.</p>
            <div className="tagger-form-grid">
              <label><span>Status</span><select value={companyHouseStatus} onChange={(event) => setCompanyHouseStatus(event.target.value)}><option value="pending">pending</option><option value="pass">pass</option><option value="fail">fail</option></select></label>
              <label className="tagger-form-span-2"><span>Validator feedback</span><textarea rows={6} value={companyHouseNotes} onChange={(event) => setCompanyHouseNotes(event.target.value)} /></label>
            </div>
            <div className="tagger-actions">
              <button type="button" className="tagger-button primary" onClick={() => void handleCompaniesHouseValidation()}>
                Run Companies House validator
              </button>
              <button type="button" className="tagger-button secondary" onClick={() => void handleRecord()}>Record Companies House result</button>
              <a className="tagger-button secondary tagger-button-link" href="https://test-validator.companieshouse.gov.uk/" target="_blank" rel="noreferrer">Open Companies House test validator</a>
              <label className="tagger-button secondary">
                Load feedback file
                <input
                  type="file"
                  accept=".txt,.html,.xhtml,.xml,.log"
                  onChange={(event) => void handleFeedbackFile(event.target.files?.[0] || null)}
                  style={{ display: "none" }}
                />
              </label>
            </div>
            {companyHouseResult ? (
              <div className={`tagger-result ${companyHouseResult.status === "pass" ? "info" : "error"}`}>
                <strong>{companyHouseResult.heading || "Companies House validator"}</strong>
                <span>{companyHouseResult.message}</span>
                <a className="tagger-button secondary tagger-button-link" href={companyHouseResult.resultUrl} target="_blank" rel="noreferrer">Open validator result</a>
              </div>
            ) : null}
          </div>
          <div className="tagger-card">
            <h3>Validation handoff checklist</h3>
            <ul className="tagger-list">
              <li><strong>1.</strong><span>Run validation until blocking issues are zero.</span></li>
              <li><strong>2.</strong><span>Generate export and review the XHTML preview.</span></li>
              <li><strong>3.</strong><span>Download the XHTML and submit it to the Companies House test validator.</span></li>
              <li><strong>4.</strong><span>Record the external pass/fail result and any notes in this project.</span></li>
            </ul>
          </div>
        </div>
        <aside className="tagger-sidebar">
          <ExportPanel
            projectId={id}
            exportId={exportSummary?.exportId || String(latestExport?.id || "")}
            factsCount={exportSummary?.factsCount ?? Number(latestExport?.factsCount || 0)}
            hiddenFactsCount={exportSummary?.hiddenFactsCount || Number(latestExport?.hiddenFactsCount || 0)}
            contextsCount={exportSummary?.contextsCount || Number(latestExport?.contextsCount || 0)}
            unitsCount={exportSummary?.unitsCount || Number(latestExport?.unitsCount || 0)}
            contextIds={exportSummary?.contextIds || latestExport?.contextIds}
            unitIds={exportSummary?.unitIds || latestExport?.unitIds}
          />
          <div className="tagger-card">
            <h3>Generated XHTML preview</h3>
            <textarea readOnly rows={18} value={exportSummary?.content || "Generate an export to inspect the XHTML output."} />
          </div>
        </aside>
      </section>
    </main>
  );
};

export default ValidationReview;
