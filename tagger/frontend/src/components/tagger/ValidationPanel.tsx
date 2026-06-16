import type { ValidationResult } from "./types";

interface ValidationPanelProps {
  results: ValidationResult[];
}

const ValidationPanel = ({ results }: ValidationPanelProps) => {
  const errors = results.filter((result) => result.severity === "error");
  const warnings = results.filter((result) => result.severity === "warning");
  const infos = results.filter((result) => result.severity !== "error" && result.severity !== "warning");

  return (
    <div className="tagger-card">
      <h3>Validation panel</h3>
      <div className="tagger-actions">
        <span className="tagger-pill">{errors.length} error(s)</span>
        <span className="tagger-pill">{warnings.length} warning(s)</span>
        <span className="tagger-pill">{infos.length} info item(s)</span>
      </div>
      <ul className="tagger-list">
        {results.map((result, index) => (
          <li key={`${result.source}-${index}`} className={`tagger-result ${result.severity}`}>
            <strong>{result.qname || result.source}</strong>
            <span>{result.message}</span>
            {result.relatedFieldId ? <span className="tagger-muted">Field: {result.relatedFieldId}</span> : null}
            {result.ruleId ? <span className="tagger-muted">Rule: {result.ruleId}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ValidationPanel;
