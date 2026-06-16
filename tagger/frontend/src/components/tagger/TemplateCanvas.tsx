import { useMemo, useRef } from "react";

interface TemplateCanvasProps {
  html: string;
  fieldOrder: string[];
  onFieldInput: (fieldId: string, rawValue: string) => void;
  onBulkFieldInput: (updates: Array<{ fieldId: string; rawValue: string; sourceType: string }>) => void;
  onFieldSelect: (fieldId: string) => void;
}

const TemplateCanvas = ({ html, fieldOrder, onFieldInput, onBulkFieldInput, onFieldSelect }: TemplateCanvasProps) => {
  const markup = useMemo(() => ({ __html: html }), [html]);
  const canvasRef = useRef<HTMLDivElement | null>(null);

  const focusField = (fieldId: string) => {
    const nextField = canvasRef.current?.querySelector<HTMLElement>(`.tagger-editable-field[data-field-id="${CSS.escape(fieldId)}"]`);
    if (!nextField) {
      return;
    }
    nextField.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(nextField);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);
  };

  return (
    <div
      ref={canvasRef}
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
      onInputCapture={(event) => {
        const target = event.target as HTMLElement;
        const fieldId = target.dataset.fieldId;
        if (!fieldId || !canvasRef.current) {
          return;
        }
        const value = target.textContent || "";
        const relatedFields = canvasRef.current.querySelectorAll<HTMLElement>(`.tagger-editable-field[data-field-id="${CSS.escape(fieldId)}"]`);
        relatedFields.forEach((node) => {
          if (node !== target) {
            node.textContent = value;
          }
        });
      }}
      onKeyDownCapture={(event) => {
        const target = event.target as HTMLElement;
        const fieldId = target.dataset.fieldId;
        if (!fieldId || event.key !== "Tab") {
          return;
        }
        event.preventDefault();
        const currentIndex = fieldOrder.indexOf(fieldId);
        if (currentIndex === -1) {
          return;
        }
        const offset = event.shiftKey ? -1 : 1;
        const nextFieldId = fieldOrder[currentIndex + offset];
        if (nextFieldId) {
          queueMicrotask(() => focusField(nextFieldId));
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
