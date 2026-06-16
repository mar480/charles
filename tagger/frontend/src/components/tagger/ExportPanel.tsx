interface ExportPanelProps {
  projectId: string;
  exportId?: string;
  factsCount?: number;
  hiddenFactsCount?: number;
  contextsCount?: number;
  unitsCount?: number;
  contextIds?: string[];
  unitIds?: string[];
}

const ExportPanel = ({
  projectId,
  exportId,
  factsCount,
  hiddenFactsCount,
  contextsCount,
  unitsCount,
  contextIds,
  unitIds,
}: ExportPanelProps) => {
  return (
    <div className="tagger-card">
      <h3>Export summary</h3>
      <table className="tagger-table">
        <tbody>
          <tr><th>Export id</th><td>{exportId || "Not generated"}</td></tr>
          <tr><th>Facts</th><td>{factsCount ?? 0}</td></tr>
          <tr><th>Hidden facts</th><td>{hiddenFactsCount ?? 0}</td></tr>
          <tr><th>Contexts</th><td>{contextsCount ?? 0}</td></tr>
          <tr><th>Units</th><td>{unitsCount ?? 0}</td></tr>
          <tr><th>Context ids</th><td>{contextIds?.join(", ") || "Not generated"}</td></tr>
          <tr><th>Unit ids</th><td>{unitIds?.join(", ") || "Not generated"}</td></tr>
        </tbody>
      </table>
      {exportId ? <a className="tagger-button secondary tagger-button-link" href={`/api/tagger/projects/${projectId}/exports/${exportId}`}>Download XHTML</a> : null}
    </div>
  );
};

export default ExportPanel;
