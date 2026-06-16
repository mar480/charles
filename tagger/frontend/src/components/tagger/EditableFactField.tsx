interface EditableFactFieldProps {
  label: string;
  value: string;
  state: string;
}

const EditableFactField = ({ label, value, state }: EditableFactFieldProps) => {
  return (
    <div className="tagger-inline-field">
      <strong>{label}</strong>
      <span>{value || "Empty"}</span>
      <span className="tagger-pill">{state}</span>
    </div>
  );
};

export default EditableFactField;

