import { useEffect, useState } from "react";

import type { ConceptChoice, TaggerTemplateField } from "./types";

interface ConceptOverridePanelProps {
  field?: TaggerTemplateField;
  currentOverrideQname?: string;
  onConceptChosen: (concept: ConceptChoice | null) => void;
}

const ConceptOverridePanel = ({
  field,
  currentOverrideQname,
  onConceptChosen,
}: ConceptOverridePanelProps) => {
  const [qname, setQname] = useState("");

  useEffect(() => {
    setQname(currentOverrideQname || "");
  }, [currentOverrideQname, field?.fieldId]);

  if (!field) {
    return (
      <div className="tagger-card">
        <h3>Concept override</h3>
        <p className="tagger-muted">Select a template field first, then enter an override QName here.</p>
      </div>
    );
  }

  return (
    <div className="tagger-card">
      <h3>Concept override</h3>
      <p className="tagger-muted">
        Enter a replacement QName for <strong>{field.label}</strong> if the default concept mapping is not right.
      </p>
      <div className="tagger-form-grid">
        <label className="tagger-form-span-2">
          <span>Override QName</span>
          <input
            type="text"
            value={qname}
            onChange={(event) => setQname(event.target.value)}
            placeholder={field.concept.qname}
          />
        </label>
      </div>
      <div className="tagger-actions">
        <button
          type="button"
          className="tagger-button secondary"
          onClick={() => onConceptChosen(qname.trim() ? { qname: qname.trim(), label: field.label } : null)}
        >
          Use override
        </button>
        <button
          type="button"
          className="tagger-button secondary"
          onClick={() => {
            setQname("");
            onConceptChosen(null);
          }}
        >
          Clear draft
        </button>
      </div>
      <p className="tagger-muted">Expected format: `prefix:LocalName`, for example `core:Revenue`.</p>
    </div>
  );
};

export default ConceptOverridePanel;
