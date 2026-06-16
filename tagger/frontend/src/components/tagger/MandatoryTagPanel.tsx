import type { ValidationResult } from "./types";

interface MandatoryTagPanelProps {
  results: ValidationResult[];
}

const MandatoryTagPanel = ({ results }: MandatoryTagPanelProps) => {
  const mandatoryResults = results.filter((result) => result.source === "mandatory-tags");
  const blockingCount = mandatoryResults.filter((result) => result.severity === "error").length;

  return (
    <div className="tagger-card">
      <h3>Mandatory Companies House and FRC tags</h3>
      <div className="tagger-actions">
        <span className="tagger-pill">{blockingCount} blocking issue(s)</span>
        <span className="tagger-pill">{mandatoryResults.length} total check(s)</span>
      </div>
      <ul className="tagger-list">
        {mandatoryResults.map((result, index) => (
          <li key={`${result.source}-${index}`} className={`tagger-result ${result.severity}`}>
            <strong>{result.qname || result.source}</strong>
            <span>{result.message}</span>
            {result.relatedFieldId ? <span className="tagger-muted">Field: {result.relatedFieldId}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default MandatoryTagPanel;
