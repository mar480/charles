import type { ImportReviewData } from "./types";

interface ImportReviewProps {
  review: ImportReviewData;
}

const ImportReview = ({ review }: ImportReviewProps) => {
  return (
    <div className="tagger-card">
      <h3>Import review</h3>
      <p>{review.sourceLabel}: {review.matchedCount} matched field updates.</p>
      <p>{review.unmatchedCount} unmatched rows.</p>
      <p>{review.overwrittenCount} existing values would be overwritten.</p>
      <p>{review.warningsCount} import warning(s).</p>
      {review.matchedFieldIds.length ? (
        <>
          <h4>Matched fields</h4>
          <ul className="tagger-list">
            {review.matchedFieldIds.slice(0, 12).map((fieldId) => (
              <li key={fieldId}>
                <strong>{fieldId}</strong>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {review.overwrittenFields.length ? (
        <>
          <h4>Overwritten values</h4>
          <ul className="tagger-list">
            {review.overwrittenFields.slice(0, 8).map((entry, index) => (
              <li key={`overwrite-${index}`}>
                <strong>{String(entry.fieldId || "field")}</strong>
                <span>{String(entry.previousValue || "")} → {String(entry.incomingValue || "")}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {review.unmatchedRows.length ? (
        <>
          <h4>Unmatched rows</h4>
          <ul className="tagger-list">
            {review.unmatchedRows.slice(0, 8).map((entry, index) => (
              <li key={`unmatched-${index}`}>
                <strong>{String(entry.reason || "Unmatched")}</strong>
                <span>{JSON.stringify(entry.row || entry)}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {review.warnings.length ? (
        <>
          <h4>Warnings</h4>
          <ul className="tagger-list">
            {review.warnings.slice(0, 8).map((entry, index) => (
              <li key={`warning-${index}`}>
                <strong>{String(entry.fieldId || "warning")}</strong>
                <span>{String(entry.message || "")}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
};

export default ImportReview;
