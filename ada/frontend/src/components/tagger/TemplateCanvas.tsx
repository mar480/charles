import { useMemo } from "react";

interface TemplateCanvasProps {
  html: string;
  fieldOrder: string[];
  onFieldInput: (fieldId: string, rawValue: string) => void;
  onBulkFieldInput: (updates: Array<{ fieldId: string; rawValue: string; sourceType: string }>) => void;
  onFieldSelect: (fieldId: string) => void;
}

const TemplateCanvas = ({ html, fieldOrder, onFieldInput, onBulkFieldInput, onFieldSelect }: TemplateCanvasProps) => {
  const markup = useMemo(() => ({ __html: html }), [html]);

  return (
    <div
      className="tagger-template-canvas"
      onBlurCapture={(event) => {
        const target = event.target as HTMLElement;
        const fieldId = target.dataset.fieldId;
        if (!fieldId) {
          return;
        }
        onFieldInput(fieldId, target.textContent || "");
      }}
      onClickCapture={(event) => {
        const target = event.target as HTMLElement;
        const fieldId = target.dataset.fieldId;
        if (fieldId) {
          onFieldSelect(fieldId);
        }
      }}
      onPasteCapture={(event) => {
        const target = event.target as HTMLElement;
        const fieldId = target.dataset.fieldId;
        if (!fieldId) {
          return;
        }
        const clipboardText = event.clipboardData.getData("text/plain");
        if (!clipboardText.includes("\n") && !clipboardText.includes("\t")) {
          return;
        }
        event.preventDefault();
        const startIndex = fieldOrder.indexOf(fieldId);
        if (startIndex === -1) {
          return;
        }
        const pastedValues = clipboardText
          .split(/\r?\n/)
          .flatMap((row) => row.split("\t"))
          .map((value) => value.trim())
          .filter((value) => value.length > 0);
        const updates = pastedValues
          .map((rawValue, index) => ({ fieldId: fieldOrder[startIndex + index], rawValue, sourceType: "paste" }))
          .filter((update) => Boolean(update.fieldId));
        if (!updates.length) {
          return;
        }
        onBulkFieldInput(updates);
      }}
      dangerouslySetInnerHTML={markup}
    />
  );
};

export default TemplateCanvas;
