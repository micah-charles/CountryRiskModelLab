import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function ResidualChart({ data }: { data?: unknown }) {
  const rows = Array.isArray(data) ? data as Record<string, unknown>[] : [];
  if (!rows.length) return null;
  return (
    <section className="panel chart-panel">
      <h3>Residuals</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="residual" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

