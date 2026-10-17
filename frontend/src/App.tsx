import { useState } from "react";
import { Layout } from "./components/Layout";
import type { PageKey } from "./components/Sidebar";
import { AdminLessonsPage } from "./routes/AdminLessonsPage";
import { DatasetPage } from "./routes/DatasetPage";
import { FormulaPlaygroundPage } from "./routes/FormulaPlaygroundPage";
import { ForecastingLabPage } from "./routes/ForecastingLabPage";
import { HistoricalEventLabPage } from "./routes/HistoricalEventLabPage";
import { HomePage } from "./routes/HomePage";
import { ImfConnectorPage } from "./routes/ImfConnectorPage";
import { ModelReviewPage } from "./routes/ModelReviewPage";
import { RegressionLabPage } from "./routes/RegressionLabPage";
import { VarLabPage } from "./routes/VarLabPage";
import { ResearchCasesPage } from "./routes/ResearchCasesPage";
import { IndicatorRegistryPage } from "./routes/IndicatorRegistryPage";

export default function App() {
  const [page, setPage] = useState<PageKey>("home");
  const [activeDatasetId, setActiveDatasetId] = useState("sample_country_risk_quarterly");
  const [lastModelResult, setLastModelResult] = useState<Record<string, unknown> | null>(null);
  const [activeCaseId, setActiveCaseId] = useState("uk_2022_mini_budget_ldi");
  const [formulaNavigation, setFormulaNavigation] = useState<{ formulaId: string } | null>(null);

  function openFormula(formulaId: string) {
    setFormulaNavigation({ formulaId });
    setPage("formulas");
  }

  return (
    <Layout active={page} onNavigate={setPage}>
      {page === "home" && <HomePage onNavigate={setPage} />}
      {page === "cases" && <ResearchCasesPage onNavigate={setPage} activeCaseId={activeCaseId} setActiveCaseId={setActiveCaseId} />}
      {(page === "event" || page === "formulas") && <div style={{ display: page === "event" ? "block" : "none" }}><HistoricalEventLabPage activeCaseId={activeCaseId} setActiveCaseId={setActiveCaseId} onNavigate={setPage} onOpenFormula={openFormula} /></div>}
      {page === "dataset" && <DatasetPage activeDatasetId={activeDatasetId} setActiveDatasetId={setActiveDatasetId} />}
      {page === "imf" && <ImfConnectorPage onDatasetReady={setActiveDatasetId} onNavigate={setPage} />}
      {page === "indicators" && <IndicatorRegistryPage />}
      {page === "regression" && <RegressionLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "forecasting" && <ForecastingLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "var" && <VarLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "formulas" && <FormulaPlaygroundPage activeCaseId={activeCaseId} requestedFormulaId={formulaNavigation?.formulaId} onReturnToEvent={() => { setFormulaNavigation(null); setPage("event"); }} />}
      {page === "memo" && <ModelReviewPage lastModelResult={lastModelResult} />}
      {page === "lessons" && <AdminLessonsPage onNavigate={setPage} setActiveDatasetId={setActiveDatasetId} />}
    </Layout>
  );
}
