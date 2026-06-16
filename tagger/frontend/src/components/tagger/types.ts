export interface TaggerTemplateField {
  fieldId: string;
  label: string;
  valueType: string;
  concept: { qname: string };
  periodRule?: string;
  unitRule?: string;
  visibility?: "visible" | "hidden";
  required?: boolean;
  helpId?: string;
}

export interface TaggerTemplate {
  templateId: string;
  label: string;
  version: string;
  defaultFilingProfile: string;
  recommendedEntrypoint?: string;
  supportedTaxonomyYears?: string[];
  taxonomyYear?: string;
  taxonomyEntrypoint?: string;
  editableHtml?: string;
  fields: TaggerTemplateField[];
}

export interface TaggerProject {
  id: string;
  status: string;
  templateId?: string;
  filingProfile: string;
  taxonomyYear: string;
  taxonomyEntrypoint: string;
  companySnapshot: Record<string, unknown>;
  defaults: Record<string, string>;
  fields: Record<string, Record<string, unknown>>;
  facts: Record<string, Record<string, unknown>>;
  validationRuns: Array<Record<string, unknown>>;
  exports: Array<Record<string, unknown>>;
  createdAt: string;
  updatedAt: string;
}

export interface TaggerExportSummary {
  id: string;
  createdAt?: string;
  filename?: string;
  factsCount?: number;
  hiddenFactsCount?: number;
  contextsCount?: number;
  unitsCount?: number;
  contextIds?: string[];
  unitIds?: string[];
  path?: string;
}

export interface ValidationResult {
  status: string;
  severity: string;
  message: string;
  source: string;
  ruleId?: string;
  qname?: string;
  relatedFieldId?: string;
}

export interface CompaniesHouseValidationResult {
  status: string;
  fileId: string;
  resultUrl: string;
  heading?: string;
  message: string;
}

export interface ConceptChoice {
  qname: string;
  label?: string;
}

export interface ImportReviewData {
  matchedCount: number;
  unmatchedCount: number;
  overwrittenCount: number;
  warningsCount: number;
  sourceLabel: string;
  matchedFieldIds: string[];
  unmatchedRows: Array<Record<string, unknown>>;
  overwrittenFields: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
}
