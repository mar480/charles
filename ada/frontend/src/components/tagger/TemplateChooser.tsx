import type { TaggerTemplate } from "./types";

interface TemplateChooserProps {
  templates: TaggerTemplate[];
  selectedTemplateId: string;
  onSelect: (templateId: string) => void;
}

const TemplateChooser = ({ templates, selectedTemplateId, onSelect }: TemplateChooserProps) => {
  return (
    <div className="tagger-grid">
      {templates.map((template) => (
        <button
          key={template.templateId}
          type="button"
          className={`tagger-card tagger-template-card ${selectedTemplateId === template.templateId ? "is-selected" : ""}`}
          onClick={() => onSelect(template.templateId)}
        >
          <div className="tagger-eyebrow">{template.defaultFilingProfile}</div>
          <h3>{template.label}</h3>
          <p>Version {template.version}</p>
          <p>{template.recommendedEntrypoint || template.taxonomyEntrypoint}</p>
        </button>
      ))}
    </div>
  );
};

export default TemplateChooser;

