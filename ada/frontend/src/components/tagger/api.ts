import type { CompaniesHouseValidationResult, TaggerProject, TaggerTemplate, ValidationResult } from "./types";

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload as T;
}

export async function listProjects(): Promise<TaggerProject[]> {
  const response = await fetch("/api/tagger/projects");
  const payload = await parseJson<{ projects: TaggerProject[] }>(response);
  return payload.projects;
}

export async function createProject(): Promise<TaggerProject> {
  const response = await fetch("/api/tagger/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  return parseJson<TaggerProject>(response);
}

export async function getProject(projectId: string): Promise<TaggerProject> {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}`);
  return parseJson<TaggerProject>(response);
}

export async function patchProjectDefaults(projectId: string, payload: Record<string, string>) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/defaults`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<TaggerProject>(response);
}

export async function listTemplates(): Promise<TaggerTemplate[]> {
  const response = await fetch("/api/tagger/templates");
  const payload = await parseJson<{ templates: TaggerTemplate[] }>(response);
  return payload.templates;
}

export async function loadTemplate(projectId: string, templateId: string): Promise<{ project: TaggerProject; template: TaggerTemplate }> {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/load-template`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ templateId }),
  });
  return parseJson<{ project: TaggerProject; template: TaggerTemplate }>(response);
}

export async function updateField(projectId: string, fieldId: string, payload: Record<string, unknown>) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/fields/${encodeURIComponent(fieldId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<TaggerProject>(response);
}

export async function runPreflight(projectId: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/preflight`, { method: "POST" });
  return parseJson<{ status: string; results: ValidationResult[] }>(response);
}

export async function runValidation(projectId: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/validate`, { method: "POST" });
  return parseJson<{ status: string; results: ValidationResult[] }>(response);
}

export async function generateIxbrl(projectId: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/generate`, { method: "POST" });
  return parseJson<{
    exportId: string;
    content: string;
    contexts: Array<Record<string, unknown>>;
    units: Array<Record<string, unknown>>;
    facts: Array<Record<string, unknown>>;
    project: TaggerProject;
  }>(response);
}

export async function importCsv(projectId: string, content: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/import/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, apply: false }),
  });
  return parseJson<{
    review: {
      matchedFields: Record<string, Record<string, unknown>>;
      unmatchedRows: Array<Record<string, unknown>>;
      overwrittenFields: Array<Record<string, unknown>>;
      warnings: Array<Record<string, unknown>>;
    };
    project: TaggerProject;
  }>(response);
}

export async function applyCsvImport(projectId: string, content: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/import/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, apply: true }),
  });
  return parseJson<{
    review: {
      matchedFields: Record<string, Record<string, unknown>>;
      unmatchedRows: Array<Record<string, unknown>>;
      overwrittenFields: Array<Record<string, unknown>>;
      warnings: Array<Record<string, unknown>>;
    };
    project: TaggerProject;
  }>(response);
}

export async function importXlsx(projectId: string, contentBase64: string, apply = false) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/import/xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contentBase64, apply }),
  });
  return parseJson<{
    review: {
      matchedFields: Record<string, Record<string, unknown>>;
      unmatchedRows: Array<Record<string, unknown>>;
      overwrittenFields: Array<Record<string, unknown>>;
      warnings: Array<Record<string, unknown>>;
    };
    project: TaggerProject;
  }>(response);
}

export async function lookupCompaniesHouse(companyNumber: string, projectId?: string) {
  const response = await fetch("/api/tagger/companies-house/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ companyNumber, projectId }),
  });
  return parseJson<{ profile: Record<string, unknown> }>(response);
}

export async function recordCompaniesHouseResult(projectId: string, payload: Record<string, string>) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/companies-house-result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<TaggerProject>(response);
}

export async function runCompaniesHouseValidation(projectId: string) {
  const response = await fetch(`/api/tagger/projects/${encodeURIComponent(projectId)}/companies-house-validate`, {
    method: "POST",
  });
  return parseJson<{ result: CompaniesHouseValidationResult; project: TaggerProject }>(response);
}
