import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listTemplates, loadTemplate, lookupCompaniesHouse, patchProjectDefaults } from "./api";
import TemplateChooser from "./TemplateChooser";
import TaggerHelpScaffold from "./TaggerHelpScaffold";
import type { TaggerProject, TaggerTemplate } from "./types";

interface ProjectSetupWizardProps {
  project: TaggerProject;
  onProjectChange: (project: TaggerProject) => void;
}

const defaultTemplateId = "microentity-companies-house-v1";
const defaultEntrypoint = "https://xbrl.frc.org.uk/FRS-102/2024-01-01/FRS-102-2024-01-01.xsd";

const ProjectSetupWizard = ({ project, onProjectChange }: ProjectSetupWizardProps) => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TaggerTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(project.templateId || defaultTemplateId);
  const [formValues, setFormValues] = useState<Record<string, string>>({
    "company.crn": String(project.defaults["company.crn"] || ""),
    "company.name": String(project.defaults["company.name"] || ""),
    "company.addressLine1": String(project.defaults["company.addressLine1"] || ""),
    "company.addressLine2": String(project.defaults["company.addressLine2"] || ""),
    "company.city": String(project.defaults["company.city"] || ""),
    "company.region": String(project.defaults["company.region"] || ""),
    "company.postcode": String(project.defaults["company.postcode"] || ""),
    "company.registeredOfficeImportedFromCh": String(project.defaults["company.registeredOfficeImportedFromCh"] || "false"),
    "company.registeredOfficeConfirmed": String(project.defaults["company.registeredOfficeConfirmed"] || "false"),
    "project.currentPeriodStart": String(project.defaults["project.currentPeriodStart"] || "2023-11-01"),
    "project.currentPeriodEnd": String(project.defaults["project.currentPeriodEnd"] || "2024-10-31"),
    "project.comparativePeriodStart": String(project.defaults["project.comparativePeriodStart"] || "2022-11-01"),
    "project.comparativePeriodEnd": String(project.defaults["project.comparativePeriodEnd"] || "2023-10-31"),
    "project.balanceSheetDate": String(project.defaults["project.balanceSheetDate"] || "2024-10-31"),
    "project.authorisationDate": String(project.defaults["project.authorisationDate"] || "2025-07-31"),
    "project.directorName": String(project.defaults["project.directorName"] || ""),
    "project.entityDormant": String(project.defaults["project.entityDormant"] || "false"),
    "project.entityTradingStatus": String(project.defaults["project.entityTradingStatus"] || "Trading"),
    "project.accountingStandardsApplied": String(project.defaults["project.accountingStandardsApplied"] || "bus:Micro-entities"),
    "project.accountsStatusAuditedOrUnaudited": String(project.defaults["project.accountsStatusAuditedOrUnaudited"] || "bus:AuditExempt-NoAccountantsReport"),
    "project.accountsType": String(project.defaults["project.accountsType"] || "bus:FullAccounts"),
    taxonomyYear: String(project.taxonomyYear || "2024"),
    taxonomyEntrypoint: String(project.taxonomyEntrypoint || defaultEntrypoint),
    filingProfile: String(project.filingProfile || "companies-house-microentity"),
    "project.defaultCurrency": String(project.defaults["project.defaultCurrency"] || "GBP"),
    "project.defaultScale": String(project.defaults["project.defaultScale"] || "0"),
    "project.defaultDecimals": String(project.defaults["project.defaultDecimals"] || "0"),
    "project.defaultDateFormat": String(project.defaults["project.defaultDateFormat"] || "datedaymonthyearen"),
    "project.defaultNumberFormat": String(project.defaults["project.defaultNumberFormat"] || "numdotdecimal"),
    "entity.identifierScheme": String(project.defaults["entity.identifierScheme"] || "http://www.companieshouse.gov.uk/"),
    "entity.identifierValue": String(project.defaults["entity.identifierValue"] || ""),
    "project.currentPeriodStartDisplay": String(project.defaults["project.currentPeriodStartDisplay"] || "01 November 2023"),
    "project.currentPeriodEndDisplay": String(project.defaults["project.currentPeriodEndDisplay"] || "31 October 2024"),
    "project.balanceSheetDateDisplay": String(project.defaults["project.balanceSheetDateDisplay"] || "31 October 2024"),
    "project.authorisationDateDisplay": String(project.defaults["project.authorisationDateDisplay"] || "31 July 2025"),
  });
  const [lookupState, setLookupState] = useState<string>("");
  const [lookupProfile, setLookupProfile] = useState<Record<string, unknown> | null>(
    Object.keys(project.companySnapshot || {}).length ? project.companySnapshot : null,
  );

  useEffect(() => {
    void listTemplates().then(setTemplates).catch((error: Error) => setLookupState(error.message));
  }, []);

  const updateField = (key: string, value: string) => {
    setFormValues((current) => ({ ...current, [key]: value }));
  };

  const handleLookup = async () => {
    const companyNumber = formValues["company.crn"];
    if (!companyNumber) {
      setLookupState("Enter a CRN before lookup.");
      return;
    }
    setLookupState("Looking up Companies House profile...");
    try {
      const { profile } = await lookupCompaniesHouse(companyNumber, project.id);
      setLookupProfile(profile);
      updateField("company.name", String(profile.company_name || formValues["company.name"]));
      updateField("entity.identifierValue", String(profile.company_number || companyNumber));
      setLookupState(`Lookup complete for ${String(profile.company_status || "company")}.`);
    } catch (error) {
      setLookupState(error instanceof Error ? error.message : "Lookup failed");
    }
  };

  const handleUseRegisteredOffice = () => {
    const registeredOffice = (lookupProfile?.registered_office_address as Record<string, unknown> | undefined) || {};
    updateField("company.addressLine1", String(registeredOffice.address_line_1 || ""));
    updateField("company.addressLine2", String(registeredOffice.address_line_2 || ""));
    updateField("company.city", String(registeredOffice.locality || ""));
    updateField("company.region", String(registeredOffice.region || ""));
    updateField("company.postcode", String(registeredOffice.postal_code || ""));
    updateField("company.registeredOfficeImportedFromCh", "true");
    updateField("company.registeredOfficeConfirmed", "false");
    setLookupState("Registered office copied from Companies House. Confirm it is still current before filing.");
  };

  const handleSave = async () => {
    const updatedProject = await patchProjectDefaults(project.id, formValues);
    onProjectChange(updatedProject);
    const loaded = await loadTemplate(project.id, selectedTemplateId);
    onProjectChange(loaded.project);
    navigate(`/projects/${project.id}/tag`);
  };

  return (
    <div className="tagger-layout">
      <section className="tagger-main">
        <div className="tagger-hero">
          <div>
            <div className="tagger-eyebrow">Project setup</div>
            <h1>Companies House micro-entity filing defaults</h1>
            <p className="tagger-muted">Setup captures entity defaults, periods, filing status tags, and the first template load for the tagger-first route.</p>
          </div>
          <div className="tagger-pill">{project.status}</div>
        </div>

        <div className="tagger-card">
          <h2>Company lookup</h2>
          <div className="tagger-form-grid">
            <label><span>CRN</span><input value={formValues["company.crn"]} onChange={(event) => updateField("company.crn", event.target.value)} data-help-id="setup.crnLookup" /></label>
            <label><span>Company name</span><input value={formValues["company.name"]} onChange={(event) => updateField("company.name", event.target.value)} /></label>
            <label><span>Address line 1</span><input value={formValues["company.addressLine1"]} onChange={(event) => updateField("company.addressLine1", event.target.value)} /></label>
            <label><span>Address line 2</span><input value={formValues["company.addressLine2"]} onChange={(event) => updateField("company.addressLine2", event.target.value)} /></label>
            <label><span>City</span><input value={formValues["company.city"]} onChange={(event) => updateField("company.city", event.target.value)} /></label>
            <label><span>Region</span><input value={formValues["company.region"]} onChange={(event) => updateField("company.region", event.target.value)} /></label>
            <label><span>Postcode</span><input value={formValues["company.postcode"]} onChange={(event) => updateField("company.postcode", event.target.value)} /></label>
          </div>
          <div className="tagger-actions">
            <button type="button" className="tagger-button secondary" onClick={handleLookup}>Lookup Companies House profile</button>
            <button type="button" className="tagger-button secondary" onClick={handleUseRegisteredOffice} disabled={!lookupProfile}>Use registered office from register</button>
            <span className="tagger-muted">{lookupState}</span>
          </div>
          {formValues["company.registeredOfficeImportedFromCh"] === "true" ? (
            <label className="tagger-card" style={{ display: "block" }}>
              <span style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>Registered office confirmation</span>
              <span className="tagger-muted" style={{ display: "block", marginBottom: 8 }}>
                I confirm that the registered office address copied from the Companies House register is still the correct filing address, and I understand the directors remain responsible for the accuracy of the accounts and filing details.
              </span>
              <input
                type="checkbox"
                checked={formValues["company.registeredOfficeConfirmed"] === "true"}
                onChange={(event) => updateField("company.registeredOfficeConfirmed", event.target.checked ? "true" : "false")}
              />
            </label>
          ) : null}
          {lookupProfile ? (
            <div className="tagger-card">
              <h3>Companies House profile snapshot</h3>
              <table className="tagger-table">
                <tbody>
                  <tr><th>Company number</th><td>{String(lookupProfile.company_number || formValues["company.crn"] || "")}</td></tr>
                  <tr><th>Status</th><td>{String(lookupProfile.company_status || "Not supplied")}</td></tr>
                  <tr><th>Type</th><td>{String(lookupProfile.type || "Not supplied")}</td></tr>
                  <tr><th>Registered office</th><td>{[
                    String((lookupProfile.registered_office_address as Record<string, unknown> | undefined)?.address_line_1 || ""),
                    String((lookupProfile.registered_office_address as Record<string, unknown> | undefined)?.address_line_2 || ""),
                    String((lookupProfile.registered_office_address as Record<string, unknown> | undefined)?.locality || ""),
                    String((lookupProfile.registered_office_address as Record<string, unknown> | undefined)?.postal_code || ""),
                  ].filter(Boolean).join(", ") || "Not supplied"}</td></tr>
                  <tr><th>Next accounts due</th><td>{String(((lookupProfile.accounts as Record<string, unknown> | undefined)?.next_accounts as Record<string, unknown> | undefined)?.due_on || "Not supplied")}</td></tr>
                  <tr><th>Last accounts type</th><td>{String(((lookupProfile.accounts as Record<string, unknown> | undefined)?.last_accounts as Record<string, unknown> | undefined)?.type || "Not supplied")}</td></tr>
                </tbody>
              </table>
            </div>
          ) : null}
        </div>

        <div className="tagger-card">
          <h2>Template and filing profile</h2>
          <div className="tagger-form-grid">
            <label><span>Taxonomy year</span><input value={formValues.taxonomyYear} onChange={(event) => updateField("taxonomyYear", event.target.value)} data-help-id="setup.taxonomyYear" /></label>
            <label><span>Taxonomy entrypoint</span><input value={formValues.taxonomyEntrypoint} onChange={(event) => updateField("taxonomyEntrypoint", event.target.value)} data-help-id="setup.taxonomyEntrypoint" /></label>
            <label><span>Filing profile</span><select value={formValues.filingProfile} onChange={(event) => updateField("filingProfile", event.target.value)}><option value="companies-house-microentity">companies-house-microentity</option><option value="companies-house-group-audited">companies-house-group-audited</option></select></label>
          </div>
          <TemplateChooser templates={templates} selectedTemplateId={selectedTemplateId} onSelect={setSelectedTemplateId} />
        </div>

        <div className="tagger-card">
          <h2>Reporting periods and filing defaults</h2>
          <div className="tagger-form-grid">
            <label><span>Current period start</span><input type="date" value={formValues["project.currentPeriodStart"]} onChange={(event) => updateField("project.currentPeriodStart", event.target.value)} data-help-id="setup.currentPeriodStart" /></label>
            <label><span>Current period end</span><input type="date" value={formValues["project.currentPeriodEnd"]} onChange={(event) => updateField("project.currentPeriodEnd", event.target.value)} data-help-id="setup.currentPeriodEnd" /></label>
            <label><span>Comparative period start</span><input type="date" value={formValues["project.comparativePeriodStart"]} onChange={(event) => updateField("project.comparativePeriodStart", event.target.value)} /></label>
            <label><span>Comparative period end</span><input type="date" value={formValues["project.comparativePeriodEnd"]} onChange={(event) => updateField("project.comparativePeriodEnd", event.target.value)} /></label>
            <label><span>Balance sheet date</span><input type="date" value={formValues["project.balanceSheetDate"]} onChange={(event) => updateField("project.balanceSheetDate", event.target.value)} data-help-id="setup.balanceSheetDate" /></label>
            <label><span>Date authorised for issue</span><input type="date" value={formValues["project.authorisationDate"]} onChange={(event) => updateField("project.authorisationDate", event.target.value)} data-help-id="setup.authorisationDate" /></label>
            <label><span>Director signing financial statements</span><input value={formValues["project.directorName"]} onChange={(event) => updateField("project.directorName", event.target.value)} data-help-id="setup.director" /></label>
            <label><span>Default currency</span><input value={formValues["project.defaultCurrency"]} onChange={(event) => updateField("project.defaultCurrency", event.target.value)} data-help-id="setup.defaultCurrency" /></label>
            <label><span>Default scale</span><input value={formValues["project.defaultScale"]} onChange={(event) => updateField("project.defaultScale", event.target.value)} data-help-id="setup.defaultScale" /></label>
            <label><span>Default decimals</span><input value={formValues["project.defaultDecimals"]} onChange={(event) => updateField("project.defaultDecimals", event.target.value)} data-help-id="setup.defaultDecimals" /></label>
            <label><span>Date transformation</span><input value={formValues["project.defaultDateFormat"]} onChange={(event) => updateField("project.defaultDateFormat", event.target.value)} /></label>
            <label><span>Number transformation</span><input value={formValues["project.defaultNumberFormat"]} onChange={(event) => updateField("project.defaultNumberFormat", event.target.value)} /></label>
            <label><span>Entity identifier scheme</span><input value={formValues["entity.identifierScheme"]} onChange={(event) => updateField("entity.identifierScheme", event.target.value)} /></label>
            <label><span>Entity identifier value</span><input value={formValues["entity.identifierValue"]} onChange={(event) => updateField("entity.identifierValue", event.target.value)} /></label>
          </div>
        </div>

        <div className="tagger-card">
          <h2>Mandatory filing status tags</h2>
          <div className="tagger-form-grid">
            <label><span>Entity dormant true or false</span><select value={formValues["project.entityDormant"]} onChange={(event) => updateField("project.entityDormant", event.target.value)}><option value="false">false</option><option value="true">true</option></select></label>
            <label><span>Entity trading status</span><input value={formValues["project.entityTradingStatus"]} onChange={(event) => updateField("project.entityTradingStatus", event.target.value)} /></label>
            <label><span>Accounting standards applied</span><input value={formValues["project.accountingStandardsApplied"]} onChange={(event) => updateField("project.accountingStandardsApplied", event.target.value)} /></label>
            <label><span>Accounts status audited or unaudited</span><input value={formValues["project.accountsStatusAuditedOrUnaudited"]} onChange={(event) => updateField("project.accountsStatusAuditedOrUnaudited", event.target.value)} /></label>
            <label><span>Accounts type</span><input value={formValues["project.accountsType"]} onChange={(event) => updateField("project.accountsType", event.target.value)} /></label>
          </div>
        </div>

        <div className="tagger-actions">
          <button type="button" className="tagger-button primary" onClick={() => void handleSave()}>Save setup and open workspace</button>
        </div>
      </section>

      <aside className="tagger-sidebar">
        <TaggerHelpScaffold />
      </aside>
    </div>
  );
};

export default ProjectSetupWizard;
