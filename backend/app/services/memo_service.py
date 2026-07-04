from __future__ import annotations

from typing import Any

from app.models.schemas import MemoRequest, MemoResponse


def _bullet_list(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- Not provided."


def generate_memo(request: MemoRequest) -> MemoResponse:
    result = request.model_result
    dataset = result.get("dataset") or {}
    source_type = dataset.get("source_type", "unknown")
    source_name = dataset.get("source_name", "unknown")
    variables = result.get("independent_variables") or result.get("variables") or []
    target = result.get("dependent_variable") or result.get("target_variable") or "selected target"

    markdown = [
        "# Model Review Memo",
        "",
        f"## Model Title",
        f"{result.get('model_type', 'Statistical Model')} for {target}",
        "",
        "## Analytical Question",
        request.analytical_question,
        "",
        "## Dataset and Sample Period",
        f"Dataset: {dataset.get('name', result.get('dataset_id', 'Unknown dataset'))}",
        f"Source: {source_name}",
        f"Frequency: {dataset.get('frequency', 'unknown')}",
        f"Sample period: {dataset.get('date_range', 'selected range')}",
        "",
        "## Variables Used",
        f"Target variable: {target}",
        f"Model variables: {', '.join(variables) if variables else 'See model result.'}",
        "",
        "## Methodology",
        f"The model uses {result.get('model_type', 'a statistical method')} to study country-risk relationships in the selected dataset.",
        "",
        "## Key Results",
        f"R-squared: {result.get('r_squared', 'n/a')}",
        f"Adjusted R-squared: {result.get('adjusted_r_squared', 'n/a')}",
        f"AIC: {result.get('aic', 'n/a')}",
        f"BIC: {result.get('bic', 'n/a')}",
        "",
        "## Economic Interpretation",
        "The output should be interpreted as statistical evidence that supports, but does not replace, country-risk judgement.",
        "",
        "## Diagnostic Results",
        "```json",
        str(result.get("diagnostics", {})),
        "```",
        "",
        "## Model Strengths",
        _bullet_list(result.get("strengths", [])),
        "",
        "## Model Weaknesses",
        _bullet_list(result.get("weaknesses", [])),
        "",
        "## Suggested Modifications",
        _bullet_list(result.get("suggested_modifications", [])),
        "",
        "## Final Analyst Judgement",
        request.final_analyst_judgement,
        "",
    ]

    if source_type == "imf_api":
        markdown.extend(
            [
                "## Data Source",
                "",
                "The dataset was imported from the IMF API.",
                "",
                f"Source: {source_name}",
                f"Countries: {', '.join(dataset.get('countries', []))}",
                f"Frequency: {dataset.get('frequency', 'annual')}",
                f"Date range: {dataset.get('date_range', 'selected range')}",
                "",
                "Data limitations:",
                "- Data availability may differ by country and year.",
                "- Some observations may be missing.",
                "- Annual data may be unsuitable for short-horizon forecasting.",
                "- IMF data may be revised over time.",
                "",
                "## Data Preparation",
                "",
                "The API response was transformed into a country-year panel. Each row represents one country-year observation. IMF indicator codes were mapped to platform variable names before modelling.",
                "",
            ]
        )
    elif dataset.get("notes"):
        markdown.extend(["## Data Source Notes", _bullet_list(dataset["notes"]), ""])

    markdown.extend(
        [
            "## Python Code Appendix",
            "```python",
            result.get("python_code", "# Python code preview not available."),
            "```",
            "",
            "## Analyst Notes",
            request.user_notes or "No additional notes provided.",
            "",
        ]
    )
    return MemoResponse(markdown="\n".join(markdown))

