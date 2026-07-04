export function RegressionResultTable({ coefficients }: { coefficients?: unknown }) {
  const rows = Array.isArray(coefficients) ? coefficients as Record<string, unknown>[] : [];
  if (!rows.length) return null;
  return (
    <section className="panel">
      <h3>Coefficient Table</h3>
      <table>
        <thead><tr><th>Variable</th><th>Coefficient</th><th>P-value</th><th>Interpretation</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.variable)}>
              <td>{String(row.variable)}</td>
              <td>{Number(row.coefficient).toFixed(3)}</td>
              <td>{row.p_value === null ? "n/a" : Number(row.p_value).toFixed(3)}</td>
              <td>{String(row.interpretation)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

