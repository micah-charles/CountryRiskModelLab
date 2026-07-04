export function MemoPreview({ markdown }: { markdown?: string }) {
  if (!markdown) return <div className="empty">Generate a memo to preview it here.</div>;
  return (
    <section className="panel memo">
      <h3>Memo Preview</h3>
      <textarea value={markdown} readOnly />
    </section>
  );
}

