import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function ForecastChart({ data, lines }: { data?: unknown; lines: string[] }) {
  const rows = Array.isArray(data) ? data as Record<string, unknown>[] : [];
  if (!rows.length) return null;
  return (
    <section className="panel chart-panel">
      <h3>Chart</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          {lines.map((line) => <Line key={line} type="monotone" dataKey={line} strokeWidth={2} dot={false} />)}
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

