import EditableFactField from "./EditableFactField";
import type { ConceptChoice, TaggerTemplateField } from "./types";

interface FactInspectorProps {
  field?: TaggerTemplateField;
  fieldState?: Record<string, unknown>;
  selectedConcept?: ConceptChoice | null;
  onApplyConceptOverride?: () => void;
  onClearConceptOverride?: () => void;
}

const FactInspector = ({
  field,
  fieldState,
  selectedConcept,
  onApplyConceptOverride,
  onClearConceptOverride,
}: FactInspectorProps) => {
  if (!field) {
    return (
      <div className="tagger-card">
        <h3>Fact inspector</h3>
        <p className="tagger-muted">Select a field from the template to inspect its mapped concept, period rule, and source state.</p>
      </div>
    );
  }

  return (
    <div className="tagger-card">
      <h3>Fact inspector</h3>
      <EditableFactField
        label={field.label}
        value={String(fieldState?.rawValue || "")}
        state={String(fieldState?.status || "empty")}
      />
      <table className="tagger-table">
        <tbody>
          <tr><th>Field id</th><td>{field.fieldId}</td></tr>
          <tr><th>Concept</th><td>{String(fieldState?.conceptOverrideQname || field.concept.qname)}</td></tr>
          <tr><th>Value type</th><td>{field.valueType}</td></tr>
          <tr><th>Period rule</th><td>{field.periodRule || "n/a"}</td></tr>
          <tr><th>Unit rule</th><td>{field.unitRule || "n/a"}</td></tr>
          <tr><th>Visibility</th><td>{field.visibility || "visible"}</td></tr>
          <tr><th>Source</th><td>{String(fieldState?.sourceType || "manual")}</td></tr>
        </tbody>
      </table>
      <div className="tagger-actions">
        <span className="tagger-muted">
          Suggested concept: {selectedConcept?.qname || "Select a concept in the taxonomy workbench."}
        </span>
        {onApplyConceptOverride && selectedConcept ? (
          <button type="button" className="tagger-button secondary" onClick={onApplyConceptOverride}>
            Apply concept override
          </button>
        ) : null}
        {onClearConceptOverride && fieldState?.conceptOverrideQname ? (
          <button type="button" className="tagger-button secondary" onClick={onClearConceptOverride}>
            Clear override
          </button>
        ) : null}
      </div>
    </div>
  );
};

export default FactInspector;
