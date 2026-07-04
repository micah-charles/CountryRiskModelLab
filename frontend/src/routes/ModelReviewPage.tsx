import { useState } from "react";
import { api } from "../api/client";
import { MemoPreview } from "../components/MemoPreview";

export function ModelReviewPage({ lastModelResult }: { lastModelResult: Record<string, unknown> | null }) {
  const [question, setQuestion] = useState("Which macro-financial indicators help explain country-risk outcomes?");
  const [notes, setNotes] = useState("");
  const [memo, setMemo] = useState("");
  const [error, setError] = useState("");

  async function generate() {
    if (!lastModelResult) {
      setError("Run a model first, then generate a memo.");
      return;
    }
    try {
      setError("");
      const response = await api.generateMemo({ model_result: lastModelResult, analytical_question: question, user_notes: notes });
      setMemo(response.markdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Memo generation failed.");
    }
  }

  async function copyMemo() {
    if (memo) {
      await navigator.clipboard.writeText(memo);
    }
  }

  function downloadMemo() {
    if (!memo) return;
    const blob = new Blob([memo], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "model-review-memo.md";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page">
      <header className="page-header"><h1>Model Review Memo</h1><p>Convert a model result into a structured analyst memo.</p></header>
      <section className="panel">
        <label className="field"><span>Analytical question</span><input value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
        <label className="field"><span>Analyst notes</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
        <button onClick={generate}>Generate Markdown Memo</button>
        <div className="actions">
          <button className="secondary" onClick={copyMemo} disabled={!memo}>Copy Markdown</button>
          <button className="secondary" onClick={downloadMemo} disabled={!memo}>Download .md</button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>
      <MemoPreview markdown={memo} />
    </div>
  );
}
