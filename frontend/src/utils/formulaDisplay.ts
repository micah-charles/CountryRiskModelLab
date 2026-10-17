const symbols: Record<string, string> = {
  "\\Delta": "Δ",
  "\\approx": "≈",
  "\\times": "×",
  "\\sqrt": "√",
  "\\sum": "Σ",
  "\\mathbf": "",
  "\\sigma": "σ",
  "\\rho": "ρ",
  "\\bar": "¯",
  "\\mid": "|",
  "\\le": "≤",
  "\\ge": "≥",
  "\\%": "%",
  "\\&": "&"
};

export function formatFormula(expression: string) {
  let value = expression;
  value = value.replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g, "($1) / ($2)");
  value = value.replace(/\\sqrt\{([^{}]*)\}/g, "√($1)");
  Object.entries(symbols).forEach(([token, replacement]) => { value = value.split(token).join(replacement); });
  return value.replace(/_\{([^{}]*)\}/g, "_$1").replace(/\^\{([^{}]*)\}/g, "^$1").replace(/[{}]/g, "").replace(/\\([A-Za-z]+)/g, "$1");
}
