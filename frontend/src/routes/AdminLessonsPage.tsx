import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PageKey } from "../components/Sidebar";
import type { Lesson } from "../types/lesson";

export function AdminLessonsPage({ onNavigate, setActiveDatasetId }: { onNavigate: (page: PageKey) => void; setActiveDatasetId: (id: string) => void }) {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selected, setSelected] = useState<Lesson | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.lessons().then((items) => { setLessons(items); setSelected(items[0] || null); }).catch((err) => setError(err instanceof Error ? err.message : "Could not load lessons."));
  }, []);
  function loadLesson(lesson: Lesson) {
    setActiveDatasetId(lesson.default_dataset_id);
    if (lesson.module === "regression") onNavigate("regression");
    else if (lesson.module === "forecasting") onNavigate("forecasting");
    else if (lesson.module === "var") onNavigate("var");
  }
  return (
    <div className="page">
      <header className="page-header"><h1>Admin Lessons</h1><p>JSON-driven lesson packs for country-risk modelling modules.</p></header>
      {error && <p className="error">{error}</p>}
      <div className="two-column">
        <section className="panel">
          <h3>Lessons</h3>
          {lessons.map((lesson) => <button className="list-button" key={lesson.lesson_id} onClick={() => setSelected(lesson)}>{lesson.title}</button>)}
        </section>
        {selected && (
          <section className="panel">
            <h3>{selected.title}</h3>
            <p className="muted">{selected.module} · {selected.level}</p>
            <p>{selected.analytical_question}</p>
            <h4>Learning Objectives</h4>
            <ul>{selected.learning_objectives.map((item) => <li key={item}>{item}</li>)}</ul>
            <h4>Concepts</h4>
            {selected.concepts.map((concept) => <p key={concept.name}><strong>{concept.name}:</strong> {concept.plain_english}</p>)}
            <button onClick={() => loadLesson(selected)}>Load lesson into lab</button>
          </section>
        )}
      </div>
    </div>
  );
}
