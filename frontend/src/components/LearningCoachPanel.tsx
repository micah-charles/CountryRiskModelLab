export function LearningCoachPanel({ mode }: { mode: "regression" | "forecast" | "var" }) {
  const content = {
    regression: [
      "A coefficient estimates how one explanatory variable relates to the target while holding selected variables constant.",
      "A p-value is a statistical signal, not a substitute for country-risk judgement.",
      "R-squared measures in-sample fit; it does not prove causality or forecast quality."
    ],
    forecast: [
      "ARIMA forecasts one variable from its own history.",
      "SARIMAX adds seasonal terms and external regressors such as policy rates or global risk.",
      "The lowest AIC is not automatically the best country-risk forecast."
    ],
    var: [
      "VAR lets several macro-financial variables depend on their own lags and each other's lags.",
      "Lag length controls how far back the model looks.",
      "Impulse responses need careful economic interpretation."
    ]
  }[mode];
  return (
    <aside className="coach">
      <h3>Learning Coach</h3>
      {content.map((item) => <p key={item}>{item}</p>)}
    </aside>
  );
}

