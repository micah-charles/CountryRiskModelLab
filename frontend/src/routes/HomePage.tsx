import type { PageKey } from "../components/Sidebar";

export function HomePage({ onNavigate }: { onNavigate: (page: PageKey) => void }) {
  const cards: { page: PageKey; title: string; body: string }[] = [
    { page: "dataset", title: "Dataset Admin", body: "Load sample data, upload CSV, preview columns, and review missing values." },
    { page: "imf", title: "IMF Data Connector", body: "Fetch real macro indicators and transform them into a country-year panel." },
    { page: "regression", title: "Regression Lab", body: "Run OLS models and interpret coefficients, diagnostics, and limitations." },
    { page: "forecasting", title: "Forecasting Lab", body: "Compare ARIMA, SARIMA, SARIMAX, and educational Auto ARIMA." },
    { page: "var", title: "VAR Lab", body: "Learn lagged macro-financial interactions and simplified impulse responses." },
    { page: "memo", title: "Model Review", body: "Generate a structured Markdown model review memo." },
    { page: "lessons", title: "Admin Lessons", body: "View JSON-driven lesson packs and learning objectives." }
  ];
  return (
    <div className="page">
      <header className="page-header">
        <h1>Country Risk Statistical Model Lab</h1>
        <p>A Python-powered learning lab for country-risk analysts.</p>
      </header>
      <section className="learning-list">
        <h2>Learn how to</h2>
        <ul>
          <li>run regression models</li>
          <li>forecast macro-financial indicators</li>
          <li>compare model performance</li>
          <li>evaluate model strengths and weaknesses</li>
          <li>document findings in a model review memo</li>
        </ul>
      </section>
      <div className="card-grid">
        {cards.map((card) => (
          <button className="card" key={card.page} onClick={() => onNavigate(card.page)}>
            <h3>{card.title}</h3>
            <p>{card.body}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

