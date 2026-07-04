export function PythonCodePanel({ code }: { code?: unknown }) {
  if (!code) return null;
  return (
    <section className="panel">
      <h3>Python Code</h3>
      <pre>{String(code)}</pre>
    </section>
  );
}

