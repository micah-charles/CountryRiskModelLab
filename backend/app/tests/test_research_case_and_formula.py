from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from app.models.schemas import FormulaCalculationRequest
from app.services.formula_engine import calculate_formula
import app.services.research_case_service as research_case_service
from app.services.research_case_service import BUILT_IN_ROOT, import_case_pack, validate_case_pack_directory


PACK_ROOT = BUILT_IN_ROOT / "uk_2022_mini_budget_ldi"


def _zip_directory(root: Path, *, omit: str | None = None, unsafe_name: str | None = None) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if not path.is_file() or path.name == omit:
                continue
            archive.write(path, path.relative_to(root).as_posix())
        if unsafe_name:
            archive.writestr(unsafe_name, "unsafe")
    return output.getvalue()


def test_builtin_golden_case_is_valid_and_normalized():
    report, case = validate_case_pack_directory(PACK_ROOT, "built_in")
    assert report.valid, report.errors
    assert case is not None
    assert case.case_id == "uk_2022_mini_budget_ldi"
    assert case.formula_refs == ["RATE_DURATION_MODIFIED", "RATE_DV01", "RATE_CONVEXITY", "STRESS_SENSITIVITY"]
    assert len(case.sources) == 8
    assert case.portfolio_impacts[0]["historical_position"] is False


def test_imported_learning_cases_are_valid_and_renderable():
    for case_id, expected_formula_refs in {
        "jpy_2026_intervention_carry_unwind": ["FX_UNHEDGED_CARRY_RETURN", "FX_MOVE_PERCENT", "LEVERAGED_RETURN"],
        "global_bond_selloff_sep_2026": ["RATE_DURATION_PRICE", "RATE_DV01", "CURVE_2S10S", "NOMINAL_REAL_INFLATION_PROXY"],
    }.items():
        report, case = validate_case_pack_directory(BUILT_IN_ROOT / case_id, "built_in")
        assert report.valid, report.errors
        assert case is not None
        assert case.formula_refs == expected_formula_refs
        assert len(case.predictions) == 4
        assert case.market_series
        assert all(row.get("indicator_id") and row.get("value") is not None for row in case.market_series)


def test_missing_required_file_is_rejected():
    report, _ = validate_case_pack_directory(PACK_ROOT, "imported")
    assert "report.pdf" not in report.errors
    content = _zip_directory(PACK_ROOT, omit="sources.json")
    result = import_case_pack(content)
    assert result.valid is False
    assert any("sources.json" in error for error in result.errors)
    assert result.imported is False


def test_zip_traversal_is_rejected_before_import():
    with pytest.raises(ValueError, match="Unsafe ZIP path"):
        import_case_pack(_zip_directory(PACK_ROOT, unsafe_name="../outside.txt"))


def test_malformed_json_unsupported_schema_and_broken_references_are_rejected(tmp_path: Path):
    malformed = tmp_path / "malformed"
    shutil.copytree(PACK_ROOT, malformed)
    (malformed / "timeline.json").write_text("{not-json", encoding="utf-8")
    report, _ = validate_case_pack_directory(malformed)
    assert any("timeline.json is malformed" in error for error in report.errors)

    unsupported = tmp_path / "unsupported"
    shutil.copytree(PACK_ROOT, unsupported)
    manifest = json.loads((unsupported / "manifest.json").read_text(encoding="utf-8"))
    manifest["schema_version"] = "9.0"
    (unsupported / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    report, _ = validate_case_pack_directory(unsupported)
    assert any("Unsupported Case Pack schema version" in error for error in report.errors)

    broken_source = tmp_path / "broken-source"
    shutil.copytree(PACK_ROOT, broken_source)
    timeline = json.loads((broken_source / "timeline.json").read_text(encoding="utf-8"))
    timeline["timeline"][0]["source_ids"] = ["missing_source"]
    (broken_source / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
    report, _ = validate_case_pack_directory(broken_source)
    assert any("missing_source" in error for error in report.errors)

    broken_formula = tmp_path / "broken-formula"
    shutil.copytree(PACK_ROOT, broken_formula)
    (broken_formula / "formula_refs.json").write_text(json.dumps({"formula_refs": ["NOT_A_FORMULA"]}), encoding="utf-8")
    report, _ = validate_case_pack_directory(broken_formula)
    assert any("Formula not found" in error for error in report.errors)


def test_failed_import_is_atomic():
    result = import_case_pack(_zip_directory(PACK_ROOT, omit="sources.json"))
    assert result.valid is False
    assert result.imported is False


def test_successful_import_returns_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(research_case_service, "IMPORTED_ROOT", tmp_path / "imported")
    result = import_case_pack(_zip_directory(PACK_ROOT))
    assert result.valid is True
    assert result.imported is True
    assert result.case_summary is not None
    assert result.case_summary.case_id == "uk_2022_mini_budget_ldi"


def test_duplicate_import_preserves_existing_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imported = tmp_path / "imported"
    monkeypatch.setattr(research_case_service, "IMPORTED_ROOT", imported)
    content = _zip_directory(PACK_ROOT)
    import_case_pack(content)
    destination = imported / "uk_2022_mini_budget_ldi"
    before = {p.relative_to(destination): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="already imported"):
        import_case_pack(content)
    assert before == {p.relative_to(destination): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    assert not list(imported.glob(".*.import.lock"))


def test_import_lock_rejects_concurrent_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imported = tmp_path / "imported"
    imported.mkdir()
    monkeypatch.setattr(research_case_service, "IMPORTED_ROOT", imported)
    lock = imported / ".uk_2022_mini_budget_ldi.import.lock"
    lock.write_text("another writer")
    with pytest.raises(ValueError, match="already being imported"):
        import_case_pack(_zip_directory(PACK_ROOT))
    assert lock.read_text() == "another writer"
    assert not (imported / "uk_2022_mini_budget_ldi").exists()


def test_legacy_aliases_are_normalized_during_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    legacy = tmp_path / "legacy"
    shutil.copytree(PACK_ROOT, legacy)

    manifest = json.loads((legacy / "manifest.json").read_text(encoding="utf-8"))
    manifest["case_pack_schema_version"] = manifest.pop("schema_version")
    manifest["case_id"] = "UK_2022_MINI_BUDGET_LDI"
    (legacy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    case = json.loads((legacy / "case.json").read_text(encoding="utf-8"))
    case["case_pack_schema_version"] = case.pop("schema_version")
    case["case_id"] = "UK_2022_MINI_BUDGET_LDI"
    (legacy / "case.json").write_text(json.dumps(case), encoding="utf-8")

    predictions = json.loads((legacy / "predictions.json").read_text(encoding="utf-8"))
    for prediction in predictions["tests"]:
        prediction["question"] = prediction.pop("prompt")
        prediction["question_type"] = prediction.pop("type")
        prediction["expected_view"] = prediction.pop("expected_answer")
    (legacy / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")

    refs = json.loads((legacy / "formula_refs.json").read_text(encoding="utf-8"))
    refs["formula_refs"] = [{"formula_id": formula_id} for formula_id in refs["formula_refs"]]
    (legacy / "formula_refs.json").write_text(json.dumps(refs), encoding="utf-8")
    (legacy / "indicators.csv").unlink()

    monkeypatch.setattr(research_case_service, "IMPORTED_ROOT", tmp_path / "imported")
    result = import_case_pack(_zip_directory(legacy))
    assert result.valid is True
    assert result.imported is True
    assert result.case_summary is not None
    assert result.case_summary.case_id == "uk_2022_mini_budget_ldi"
    assert any("compatibility normalization" in warning for warning in result.warnings)


def test_dv01_known_answer_and_signed_short_position():
    result = calculate_formula(FormulaCalculationRequest(formula_id="RATE_DV01", parameters={"position_value": 100_000_000, "modified_duration": 18, "yield_shock_bp": 50}))
    assert result.outputs["dv01_per_bp"] == 180_000
    assert result.outputs["estimated_pnl"] == -9_000_000
    short = calculate_formula(FormulaCalculationRequest(formula_id="RATE_DV01", parameters={"position_value": -100_000_000, "modified_duration": 18, "yield_shock_bp": 50}))
    assert short.outputs["estimated_pnl"] == 9_000_000


def test_fx_and_global_rates_case_formulas_known_answers():
    fx_move = calculate_formula(FormulaCalculationRequest(formula_id="FX_MOVE_PERCENT", parameters={"entry_usdjpy": 160.03, "exit_usdjpy": 155.39}))
    assert round(fx_move.outputs["move_percent"], 4) == -2.8995

    carry = calculate_formula(FormulaCalculationRequest(formula_id="FX_UNHEDGED_CARRY_RETURN", parameters={"entry_usdjpy": 160.03, "exit_usdjpy": 155.39, "holding_days": 2, "usd_asset_yield_annual": 0.05, "jpy_funding_rate_annual": 0.01}))
    assert carry.outputs["unlevered_return"] == -0.028782

    leveraged = calculate_formula(FormulaCalculationRequest(formula_id="LEVERAGED_RETURN", parameters={"unlevered_return": carry.outputs["unlevered_return"], "leverage": 3}))
    assert leveraged.outputs["leveraged_return"] == -0.086346

    curve = calculate_formula(FormulaCalculationRequest(formula_id="CURVE_2S10S", parameters={"yield_2y": 4.18, "yield_10y": 4.79}))
    assert curve.outputs["spread_bp"] == 61

    gap = calculate_formula(FormulaCalculationRequest(formula_id="NOMINAL_REAL_INFLATION_PROXY", parameters={"nominal_10y_pct": 4.96, "real_10y_pct": 2.60}))
    assert gap.outputs["gap_pct"] == 2.36


def test_duration_convexity_and_portfolio_variance_known_answers():
    duration = calculate_formula(FormulaCalculationRequest(formula_id="RATE_DURATION_MODIFIED", parameters={"macaulay_duration": 18, "yield_rate": 0.05, "frequency": 1}))
    assert round(duration.outputs["modified_duration"], 2) == 17.14
    convexity = calculate_formula(FormulaCalculationRequest(formula_id="RATE_CONVEXITY", parameters={"position_value": 100_000_000, "modified_duration": 18, "convexity": 350, "yield_shock_bp": 100}))
    assert convexity.outputs["convexity_adjusted_pnl"] == -16_250_000
    portfolio = calculate_formula(FormulaCalculationRequest(formula_id="PORT_TWO_ASSET_VARIANCE", parameters={"weight_1": 0.6, "weight_2": 0.4, "volatility_1": 0.1, "volatility_2": 0.2, "correlation": 0.2}))
    assert round(portfolio.outputs["portfolio_volatility"], 4) == 0.1092
    matrix_portfolio = calculate_formula(FormulaCalculationRequest(formula_id="PORT_N_ASSET_VARIANCE", parameters={"weights": [0.6, 0.4], "volatilities": [0.1, 0.2], "correlation_matrix": [[1, 0.2], [0.2, 1]]}))
    assert round(matrix_portfolio.outputs["portfolio_volatility"], 4) == 0.1092
    portfolio_volatility = calculate_formula(FormulaCalculationRequest(formula_id="PORTFOLIO_VOLATILITY", parameters={"portfolio_variance": 0.01192464}))
    assert round(portfolio_volatility.outputs["portfolio_volatility"], 4) == 0.1092


@pytest.mark.parametrize("formula_id", ["STAT_VARIANCE", "STAT_STANDARD_DEVIATION"])
def test_sample_statistics_require_at_least_two_observations(formula_id: str):
    with pytest.raises(ValueError, match="at least two observations"):
        calculate_formula(FormulaCalculationRequest(formula_id=formula_id, parameters={"values": [4.2]}))


def test_correlation_bound_and_historical_tail_validation():
    with pytest.raises(ValueError, match="Correlation must be"):
        calculate_formula(FormulaCalculationRequest(formula_id="PORT_TWO_ASSET_VARIANCE", parameters={"weight_1": 0.5, "weight_2": 0.5, "volatility_1": 0.1, "volatility_2": 0.1, "correlation": 1.1}))
    es = calculate_formula(FormulaCalculationRequest(formula_id="ES_HISTORICAL", parameters={"returns": [-0.03, -0.01, 0, 0.01, 0.02], "position_value": 100_000_000, "confidence": 0.8}))
    assert es.outputs["expected_shortfall"] >= es.outputs["var"]
