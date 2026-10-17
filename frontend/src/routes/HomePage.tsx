import type { PageKey } from "../components/Sidebar";

export function HomePage({ onNavigate }: { onNavigate: (page: PageKey) => void }) {
  const cards: { page: PageKey; title: string; body: string }[] = [
    { page: "cases", title: "Research Cases", body: "Import evidence-based Case Packs and learn from real historical events." },
    { page: "event", title: "Historical Event Lab", body: "Predict, reveal, explain, quantify, and decide through a complete market-risk case." },
    { page: "dataset", title: "Dataset Admin", body: "Load sample data, upload CSV, preview columns, and review missing values." },
    { page: "imf", title: "IMF Data Connector", body: "Fetch real macro indicators and transform them into a country-year panel." },
    { page: "indicators", title: "Indicator Registry", body: "Browse shared indicator definitions, units, frequency, and provenance." },
    { page: "regression", title: "Regression Lab", body: "Run OLS models and interpret coefficients, diagnostics, and limitations." },
    { page: "forecasting", title: "Forecasting Lab", body: "Compare ARIMA, SARIMA, SARIMAX, and educational Auto ARIMA." },
    { page: "var", title: "Vector Autoregression Lab", body: "Learn lagged macro-financial interactions and simplified impulse responses." },
    { page: "formulas", title: "Formula Playground", body: "Change risk inputs at runtime, inspect every calculation step, and reset safely." },
    { page: "memo", title: "Model Review", body: "Generate a structured Markdown model review memo." },
    { page: "lessons", title: "Lessons", body: "View JSON-driven lesson packs and learning objectives." }
  ];
  return (
    <div className="page">
      <header className="page-header">
        <h1>Risk Research Lab</h1>
        <p>Country research, market events, and risk mathematics in one evidence-based learning environment.</p>
      </header>
      <section className="learning-list">
        <h2>Learn how to</h2>
        <ul>
          <li>understand what happened and why</li>
          <li>predict market direction before seeing the outcome</li>
          <li>connect market moves to portfolio risk</li>
          <li>calculate sensitivities transparently</li>
          <li>document decisions and model limitations</li>
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
