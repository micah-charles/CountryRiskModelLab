import { useState } from "react";
import { Layout } from "./components/Layout";
import type { PageKey } from "./components/Sidebar";
import { AdminLessonsPage } from "./routes/AdminLessonsPage";
import { DatasetPage } from "./routes/DatasetPage";
import { ForecastingLabPage } from "./routes/ForecastingLabPage";
import { HomePage } from "./routes/HomePage";
import { ImfConnectorPage } from "./routes/ImfConnectorPage";
import { ModelReviewPage } from "./routes/ModelReviewPage";
import { RegressionLabPage } from "./routes/RegressionLabPage";
import { VarLabPage } from "./routes/VarLabPage";

export default function App() {
  const [page, setPage] = useState<PageKey>("home");
  const [activeDatasetId, setActiveDatasetId] = useState("sample_country_risk_quarterly");
  const [lastModelResult, setLastModelResult] = useState<Record<string, unknown> | null>(null);

  return (
    <Layout active={page} onNavigate={setPage}>
      {page === "home" && <HomePage onNavigate={setPage} />}
      {page === "dataset" && <DatasetPage activeDatasetId={activeDatasetId} setActiveDatasetId={setActiveDatasetId} />}
      {page === "imf" && <ImfConnectorPage onDatasetReady={setActiveDatasetId} onNavigate={setPage} />}
      {page === "regression" && <RegressionLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "forecasting" && <ForecastingLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "var" && <VarLabPage activeDatasetId={activeDatasetId} setLastModelResult={setLastModelResult} />}
      {page === "memo" && <ModelReviewPage lastModelResult={lastModelResult} />}
      {page === "lessons" && <AdminLessonsPage onNavigate={setPage} setActiveDatasetId={setActiveDatasetId} />}
    </Layout>
  );
}
