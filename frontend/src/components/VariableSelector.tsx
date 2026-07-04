export function VariableSelector({ label, values, selected, onChange, multiple = false }: { label: string; values: string[]; selected: string | string[]; onChange: (value: string | string[]) => void; multiple?: boolean }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select
        multiple={multiple}
        value={selected}
        onChange={(event) => {
          if (multiple) {
            onChange(Array.from(event.target.selectedOptions).map((option) => option.value));
          } else {
            onChange(event.target.value);
          }
        }}
      >
        {values.map((value) => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
  );
}

