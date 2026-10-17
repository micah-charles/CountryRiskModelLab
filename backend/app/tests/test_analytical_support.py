import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.analytical_support_service import validate_analytical_support
from app.services.research_case_service import BUILT_IN_ROOT, validate_case_pack_directory


PACK_ROOT = BUILT_IN_ROOT / "uk_2022_mini_budget_ldi"


def test_ldi_case_uses_typed_prediction_questions_and_reusable_support():
    case = TestClient(app).get("/api/research-cases/uk_2022_mini_budget_ldi").json()
    assert [item["type"] for item in case["predictions"]] == ["directional", "directional", "binary", "directional"]
    assert case["predictions"][2]["options"] == ["yes", "no", "uncertain"]
    assert case["predictions"][0]["analytical_support"]["reference_id"] == "FISCAL_TO_LONG_YIELDS"
    assert case["predictions"][1]["analytical_support"]["reference_id"] == "RATE_BOND_PRICE_SENSITIVITY"


def test_analytical_support_endpoint_resolves_formula_and_transmission():
    client = TestClient(app)
    formula = client.get("/api/analytical-support/formula/RATE_BOND_PRICE_SENSITIVITY")
    assert formula.status_code == 200
    assert formula.json()["support_type"] == "formula"
    assert formula.json()["formula"]["support_type"] == "formula"

    transmission = client.get("/api/analytical-support/transmission/FISCAL_TO_LONG_YIELDS")
    assert transmission.status_code == 200
    assert transmission.json()["transmission"]["channels"]
    assert transmission.json()["transmission"]["countervailing_channels"]


def test_broken_analytical_support_reference_rejects_case(tmp_path: Path):
    broken = tmp_path / "broken-support"
    shutil.copytree(PACK_ROOT, broken)
    predictions = json.loads((broken / "predictions.json").read_text(encoding="utf-8"))
    predictions["tests"][0]["analytical_support"]["reference_id"] = "MISSING_TRANSMISSION"
    (broken / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
    report, _ = validate_case_pack_directory(broken)
    assert report.valid is False
    assert any("Transmission not found" in error for error in report.errors)


def test_before_reveal_support_cannot_contain_protected_actual_data():
    try:
        validate_analytical_support({"type": "transmission", "reference_id": "FISCAL_TO_LONG_YIELDS", "actual_value": 50, "available_before_reveal": True})
    except ValueError as exc:
        assert "protected actual" in str(exc)
    else:
        raise AssertionError("Protected actual data was accepted in before-reveal support.")


def test_case_validation_checks_raw_before_reveal_support_payload(tmp_path: Path):
    broken = tmp_path / "protected-support"
    shutil.copytree(PACK_ROOT, broken)
    predictions = json.loads((broken / "predictions.json").read_text(encoding="utf-8"))
    predictions["tests"][0]["analytical_support"]["actual_value"] = 50
    (broken / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
    report, _ = validate_case_pack_directory(broken)
    assert report.valid is False
    assert any("protected actual" in error for error in report.errors)
