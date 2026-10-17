"""Portable synthetic fixtures when private research packs are not installed.

These are generated only in pytest's temporary directory. They are not market
observations, are never installed as application seed data, and contain no
copied research reports. Local runs continue to validate actual private packs
when they exist.
"""
from __future__ import annotations

import json
import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_test_state(tmp_path_factory):
    """Never write test audit events, registries or imports into the workspace."""
    from app.services import dataset_registry_service as registry
    from app.services import research_case_service as cases

    root = tmp_path_factory.mktemp("econ_test_state")
    patch = pytest.MonkeyPatch()
    for key, value in {
        "AUDIT_LOG_PATH": str(root / "audit.jsonl"),
        "AUDIT_SINKS": "local",
        "MODEL_APPROVALS_PATH": str(root / "model_approvals.json"),
        "DATASET_REGISTRY_BACKEND": "json",
        "DATASET_REGISTRY_SQLITE_PATH": str(root / "registry.sqlite3"),
    }.items():
        patch.setenv(key, value)
    old_dir, old_path = registry.REGISTRY_DIR, registry.REGISTRY_PATH
    for module in list(sys.modules.values()):
        if module is None or not getattr(module, "__name__", "").startswith("app."):
            continue
        if getattr(module, "REGISTRY_DIR", None) == old_dir:
            patch.setattr(module, "REGISTRY_DIR", root / "registry")
        if getattr(module, "REGISTRY_PATH", None) == old_path:
            patch.setattr(module, "REGISTRY_PATH", root / "registry" / "registry.json")
    patch.setattr(cases, "IMPORTED_ROOT", root / "cases")
    registry.register_sample_datasets()
    yield root
    patch.undo()


@pytest.fixture(scope="session", autouse=True)
def portable_research_fixtures(tmp_path_factory, isolated_test_state):
    from app.services import research_case_service as service

    if (service.BUILT_IN_ROOT / "uk_2022_mini_budget_ldi" / "manifest.json").exists():
        yield
        return
    root = tmp_path_factory.mktemp("synthetic_case_contracts")
    definitions = {
        "uk_2022_mini_budget_ldi": ["RATE_DURATION_MODIFIED", "RATE_DV01", "RATE_CONVEXITY", "STRESS_SENSITIVITY"],
        "jpy_2026_intervention_carry_unwind": ["FX_UNHEDGED_CARRY_RETURN", "FX_MOVE_PERCENT", "LEVERAGED_RETURN"],
        "global_bond_selloff_sep_2026": ["RATE_DURATION_PRICE", "RATE_DV01", "CURVE_2S10S", "NOMINAL_REAL_INFLATION_PROXY"],
    }
    for case_id, formula_refs in definitions.items():
        folder = root / case_id
        folder.mkdir()
        support = [("transmission", "FISCAL_TO_LONG_YIELDS"), ("formula", "RATE_BOND_PRICE_SENSITIVITY"), ("transmission", "LDI_DELEVERAGING_LOOP"), ("transmission", "FISCAL_CONFIDENCE_TO_FX")]
        predictions = []
        for i, (kind, reference) in enumerate(support):
            predictions.append({"prediction_id": f"p{i+1}", "prompt": "Synthetic schema test question; not a historical claim.", "type": "binary" if i == 2 else "directional", "expected_answer": "no" if i == 2 else "up", "options": ["yes", "no", "uncertain"] if i == 2 else ["up", "down", "uncertain"], "actual_direction": "up", "source_ids": ["synthetic_source_0"], "analytical_support": {"type": kind, "reference_id": reference, "available_before_reveal": True}})
        payloads = {
            "case.json": {"schema_version": "1.0", "case_id": case_id, "title": f"SYNTHETIC TEST FIXTURE: {case_id}", "status": "synthetic_test_only", "primary_country": "TEST", "event_start": "2000-01-01", "event_end": "2000-01-02", "trigger": {"date": "2000-01-01", "description": "Synthetic test fixture; no historical evidence.", "source_ids": ["synthetic_source_0"]}, "indicator_ids": [], "evidence_policy": {"synthetic_test_only": True}},
            "timeline.json": {"timeline": [{"date": "2000-01-01", "event": "Synthetic test event", "source_ids": ["synthetic_source_0"]}]},
            "predictions.json": {"schema_version": "1.0", "tests": predictions},
            "sources.json": {"sources": [{"source_id": f"synthetic_source_{i}", "title": "Synthetic test placeholder", "url": f"https://example.invalid/test/{i}"} for i in range(8)]},
            "consequence_graph.json": {"nodes": [{"id": "synthetic_a"}, {"id": "synthetic_b"}], "edges": [{"from": "synthetic_a", "to": "synthetic_b", "source_ids": ["synthetic_source_0"]}]},
            "portfolio_learning.json": {"historical_position": False, "content_type": "synthetic_learning_exercise"},
            "formula_refs.json": {"formula_refs": formula_refs},
        }
        for filename, value in payloads.items():
            (folder / filename).write_text(json.dumps(value))
        csv_text = "date,indicator_id,value,unit,source_id,data_status\n2000-01-01,SYNTHETIC_TEST,1,test,synthetic_source_0,SYNTHETIC\n"
        (folder / "indicators.csv").write_text(csv_text)
        (folder / "market_series").mkdir()
        (folder / "market_series" / "synthetic.csv").write_text(csv_text)
        (folder / "README.md").write_text("Synthetic contract fixture. No historical market data.\n")
        (folder / "report.pdf").write_bytes(b"%PDF-1.4\n% Synthetic test placeholder, no research content.\n%%EOF\n")
        files = [{"path": p.relative_to(folder).as_posix()} for p in folder.rglob("*") if p.is_file()]
        (folder / "manifest.json").write_text(json.dumps({"schema_version": "1.0", "case_id": case_id, "files": files}))
    patch = pytest.MonkeyPatch()
    patch.setattr(service, "BUILT_IN_ROOT", root)
    for name, module in list(sys.modules.items()):
        if name.rsplit(".", 1)[-1] in {"test_research_case_and_formula", "test_analytical_support"}:
            patch.setattr(module, "BUILT_IN_ROOT", root, raising=False)
            patch.setattr(module, "PACK_ROOT", root / "uk_2022_mini_budget_ldi", raising=False)
    yield
    patch.undo()
