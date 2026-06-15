import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { searchConcepts } from "./services/explorerApi";
import type { SearchConceptApiResult } from "./explorerTypes";
import type { ConceptChoice } from "@/components/tagger/types";

interface TaxonomyWorkbenchPanelProps {
  year: string;
  href: string;
  initialQuery?: string;
  onConceptChosen?: (concept: ConceptChoice) => void;
}

const TaxonomyWorkbenchPanel = ({
  year,
  href,
  initialQuery = "",
  onConceptChosen,
}: TaxonomyWorkbenchPanelProps) => {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchConceptApiResult[]>([]);
  const [status, setStatus] = useState("");

  const trimmedQuery = useMemo(() => query.trim(), [query]);

  const handleSearch = async () => {
    if (!trimmedQuery) {
      return;
    }
    setStatus("Searching taxonomy...");
    try {
      const payload = await searchConcepts({
        year,
        href,
        q: trimmedQuery,
        filters: {},
        limit: 8,
        offset: 0,
      });
      setResults(payload.results || []);
      setStatus(`${payload.total || 0} matches`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Taxonomy search failed");
    }
  };

  return (
    <div className="tagger-card">
      <h3>Taxonomy workbench</h3>
      <div className="tagger-actions">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search concepts" />
        <button type="button" className="tagger-button secondary" onClick={() => void handleSearch()}>Search</button>
      </div>
      <p className="tagger-muted">{status}</p>
      <ul className="tagger-list">
        {results.map((result) => (
          <li key={result.qname}>
            <strong>{result.qname}</strong>
            <span>{result.label}</span>
            {onConceptChosen ? (
              <button
                type="button"
                className="tagger-button secondary"
                onClick={() => onConceptChosen({ qname: result.qname, label: result.label })}
              >
                Use for selected field
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      <Link className="tagger-button secondary tagger-button-link" to="/taxonomy-lab">Open full taxonomy lab</Link>
    </div>
  );
};

export default TaxonomyWorkbenchPanel;
