const TaggerHelpScaffold = () => {
  return (
    <div className="tagger-card">
      <div className="tagger-eyebrow">Help scaffold</div>
      <h3>Guidance anchors</h3>
      <ul className="tagger-list">
        <li data-help-id="help.crnLookup">CRN lookup and Companies House profile</li>
        <li data-help-id="help.taxonomyYear">Taxonomy year and entrypoint choice</li>
        <li data-help-id="help.templateChoice">Template selection and filing profile</li>
        <li data-help-id="help.mandatoryHiddenTags">Mandatory hidden tags</li>
        <li data-help-id="help.validationPanel">Validation panel and Arelle output</li>
        <li data-help-id="help.exportCompaniesHouse">Companies House test validator export</li>
      </ul>
      <div className="tagger-actions">
        <a className="tagger-button secondary tagger-button-link" href="https://developer-specs.company-information.service.gov.uk/" target="_blank" rel="noreferrer">Companies House API docs</a>
        <a className="tagger-button secondary tagger-button-link" href="https://test-validator.companieshouse.gov.uk/" target="_blank" rel="noreferrer">Companies House test validator</a>
        <a className="tagger-button secondary tagger-button-link" href="https://www.frc.org.uk/library/standards-codes-policy/accounting-and-reporting/frc-taxonomies/" target="_blank" rel="noreferrer">FRC taxonomy resources</a>
        <a className="tagger-button secondary tagger-button-link" href="https://www.gov.uk/government/organisations/charity-commission" target="_blank" rel="noreferrer">Charity Commission guidance</a>
        <a className="tagger-button secondary tagger-button-link" href="https://www.gov.uk/government/organisations/hm-revenue-customs" target="_blank" rel="noreferrer">HMRC guidance</a>
      </div>
      <p className="tagger-muted">These anchors are scaffolding for fuller guided help content tied to the tagger workflow.</p>
    </div>
  );
};

export default TaggerHelpScaffold;
