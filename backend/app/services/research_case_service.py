from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any
import zipfile

import pandas as pd

from app.models.schemas import CasePackValidation, PredictionQuestion, ResearchCase, ResearchCaseImportResponse, ResearchCaseSummary
from app.services.analytical_support_service import validate_analytical_support
from app.services.formula_engine import get_formula_definition
from app.services.indicator_registry_service import get_indicator_definition


APP_DIR = Path(__file__).resolve().parents[1]
BUILT_IN_ROOT = APP_DIR / "research_cases"
IMPORTED_ROOT = APP_DIR / "data_registry" / "cases"
SUPPORTED_SCHEMA_VERSION = "1.0"
CORE_FILES = {
    "manifest.json",
    "case.json",
    "timeline.json",
    "indicators.csv",
    "predictions.json",
    "consequence_graph.json",
    "sources.json",
    "portfolio_learning.json",
    "report.pdf",
    "README.md",
}
MAX_ZIP_FILES = 250
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
CASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,90}$")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_case_id(case_id: str) -> bool:
    return bool(CASE_ID_PATTERN.fullmatch(case_id))


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_files(manifest: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        errors.append("manifest.json must contain a files array.")
        return []
    entries: list[dict[str, Any]] = []
    for item in manifest["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("Each manifest file entry must contain a path.")
            continue
        entries.append(item)
    return entries


def _validate_relative_path(path: str) -> bool:
    pure = PurePosixPath(path.replace("\\", "/"))
    return not pure.is_absolute() and ".." not in pure.parts and str(pure) not in {"", "."}


def _find_pack_root(directory: Path) -> Path:
    manifests = list(directory.rglob("manifest.json"))
    if len(manifests) != 1:
        raise ValueError("A Case Pack must contain exactly one manifest.json.")
    return manifests[0].parent


def _source_ids(value: Any, found: set[str] | None = None, *, skip_source_registry: bool = False) -> set[str]:
    if found is None:
        found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower()
            if normalized in {"source_id", "source_ids", "source_refs", "source_ref"}:
                if isinstance(item, str):
                    found.add(item)
                elif isinstance(item, list):
                    found.update(str(entry) for entry in item)
            else:
                _source_ids(item, found)
    elif isinstance(value, list):
        for item in value:
            _source_ids(item, found)
    return found


def _source_registry(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("sources"), list):
        return [item for item in raw["sources"] if isinstance(item, dict)]
    return []


def _formula_refs(root: Path, case_raw: dict[str, Any], warnings: list[str], errors: list[str]) -> list[str]:
    path = root / "formula_refs.json"
    refs: Any = None
    if path.exists():
        try:
            refs = _json(path)
        except Exception as exc:
            errors.append(f"formula_refs.json is malformed: {exc}")
            return []
    else:
        refs = case_raw.get("formula_refs", [])
        warnings.append("formula_refs.json is absent; this legacy v1 pack has no explicit formula registry file.")
    if isinstance(refs, dict):
        refs = refs.get("formula_refs", refs.get("formulas", []))
    if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
        errors.append("Formula references must be a list of formula IDs.")
        return []
    for formula_id in refs:
        try:
            get_formula_definition(formula_id)
        except ValueError as exc:
            errors.append(str(exc))
    return list(dict.fromkeys(refs))


def _series_label(series_id: str, column: str) -> str:
    labels = {
        "usd_jpy": "USD/JPY",
        "2s10s_bp": "2s10s curve slope",
        "2y": "2-year yield",
        "5y": "5-year yield",
        "7y": "7-year yield",
        "10y": "10-year yield",
        "20y": "20-year yield",
        "30y": "30-year yield",
    }
    return labels.get(column, f"{series_id}: {column.replace('_', ' ')}")


def _series_unit(column: str) -> str:
    if column.endswith("_bp") or column in {"2s10s", "spread_bp"}:
        return "bp"
    if column in {"usd_jpy"}:
        return "JPY per USD"
    return "%"


def _normalize_market_series(series_path: Path) -> list[dict[str, Any]]:
    """Convert both long-form and simple wide CSVs into renderable observations."""
    frame = pd.read_csv(series_path).where(lambda value: pd.notna(value), None)
    series_id = series_path.stem
    metadata_columns = {"date", "value", "unit", "indicator_id", "label", "direction", "source_id", "data_status", "evidence_type", "provenance", "note"}
    if {"date", "value", "indicator_id"}.issubset(frame.columns):
        rows = frame.to_dict(orient="records")
        for row in rows:
            row["series_id"] = series_id
            row.setdefault("label", _series_label(series_id, str(row.get("indicator_id", series_id))))
            row.setdefault("data_status", row.get("provenance") or row.get("evidence_type") or "OBSERVED")
        return rows

    value_columns = [column for column in frame.columns if column not in metadata_columns]
    rows: list[dict[str, Any]] = []
    for source_row in frame.to_dict(orient="records"):
        for column in value_columns:
            value = source_row.get(column)
            if value is None:
                continue
            rows.append({
                "date": source_row.get("date"),
                "value": value,
                "unit": _series_unit(column),
                "indicator_id": f"{series_id}_{column}",
                "label": _series_label(series_id, column),
                "source_id": source_row.get("source_id"),
                "data_status": source_row.get("data_status") or source_row.get("provenance") or source_row.get("evidence_type") or "OBSERVED",
                "series_id": series_id,
            })
    return rows


def _normalize_case(root: Path, origin: str) -> ResearchCase:
    case_raw = _json(root / "case.json")
    timeline_raw = _json(root / "timeline.json")
    predictions_raw = _json(root / "predictions.json")
    graph_raw = _json(root / "consequence_graph.json")
    sources_raw = _json(root / "sources.json")
    portfolio_raw = _json(root / "portfolio_learning.json")
    indicators = pd.read_csv(root / "indicators.csv").where(lambda frame: pd.notna(frame), None).to_dict(orient="records")
    for row in indicators:
        row.setdefault("data_status", "OBSERVED")
    market_series: list[dict[str, Any]] = []
    series_root = root / "market_series"
    if series_root.exists():
        for series_path in sorted(series_root.glob("*.csv")):
            market_series.extend(_normalize_market_series(series_path))
    sources = _source_registry(sources_raw)
    predictions = predictions_raw.get("tests", []) if isinstance(predictions_raw, dict) else predictions_raw
    timeline = timeline_raw.get("events", timeline_raw.get("timeline", [])) if isinstance(timeline_raw, dict) else timeline_raw
    countries = case_raw.get("countries") or ([case_raw["primary_country"]] if case_raw.get("primary_country") else [])
    anchor_date = case_raw.get("anchor_event_date") or (case_raw.get("trigger") or {}).get("date")
    formula_refs: list[str] = []
    formula_path = root / "formula_refs.json"
    if formula_path.exists():
        raw_refs = _json(formula_path)
        formula_refs = raw_refs.get("formula_refs", raw_refs) if isinstance(raw_refs, dict) else raw_refs
    elif isinstance(case_raw.get("formula_refs"), list):
        formula_refs = case_raw["formula_refs"]
    normalized = ResearchCase(
        case_id=case_raw["case_id"],
        schema_version=case_raw.get("schema_version", SUPPORTED_SCHEMA_VERSION),
        title=case_raw.get("title", case_raw["case_id"]),
        short_title=case_raw.get("short_title") or case_raw.get("title", case_raw["case_id"]),
        summary=case_raw.get("summary") or case_raw.get("trigger", {}).get("description", ""),
        countries=countries,
        regions=case_raw.get("regions", []),
        start_date=case_raw.get("start_date") or case_raw.get("event_start"),
        end_date=case_raw.get("end_date") or case_raw.get("event_end"),
        anchor_event_date=anchor_date,
        themes=case_raw.get("themes", []),
        difficulty=case_raw.get("difficulty", "intermediate"),
        trigger=case_raw.get("trigger", {}),
        background=case_raw.get("background", case_raw.get("context", "")),
        timeline=timeline if isinstance(timeline, list) else [],
        expected_transmission=case_raw.get("expected_transmission", []),
        actual_market_moves=indicators,
        market_series=market_series,
        predictions=predictions if isinstance(predictions, list) else [],
        consequences=graph_raw if isinstance(graph_raw, dict) else {},
        portfolio_impacts=[portfolio_raw] if isinstance(portfolio_raw, dict) else [],
        formula_refs=formula_refs if isinstance(formula_refs, list) else [],
        lessons=case_raw.get("lessons", case_raw.get("learning_objectives", [])),
        sources=sources,
        datasets=case_raw.get("datasets", []),
        artifacts=case_raw.get("artifacts", {}),
        evidence_policy=case_raw.get("evidence_policy", {}),
        metadata={"origin": origin, "case_type": case_raw.get("case_type"), "status": case_raw.get("status")},
    )
    return normalized


def _summary(case: ResearchCase, root: Path, origin: str) -> ResearchCaseSummary:
    return ResearchCaseSummary(
        case_id=case.case_id,
        schema_version=case.schema_version,
        title=case.title,
        short_title=case.short_title,
        summary=case.summary,
        countries=case.countries,
        start_date=case.start_date,
        end_date=case.end_date,
        anchor_event_date=case.anchor_event_date,
        themes=case.themes,
        difficulty=case.difficulty,
        source_count=len(case.sources),
        indicator_count=len(case.actual_market_moves),
        prediction_count=len(case.predictions),
        formula_refs=case.formula_refs,
        has_report=(root / "report.pdf").exists(),
        origin="imported" if origin == "imported" else "built_in",
    )


def validate_case_pack_directory(root: Path, origin: str = "imported") -> tuple[CasePackValidation, ResearchCase | None]:
    errors: list[str] = []
    warnings: list[str] = []
    file_hashes: dict[str, str] = {}
    case_id = None
    schema_version = None
    if not root.is_dir():
        return CasePackValidation(valid=False, errors=["Case Pack root is not a directory."]), None
    present = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    missing = sorted(CORE_FILES - present)
    if missing:
        errors.append(f"Missing required files: {', '.join(missing)}.")
    try:
        manifest = _json(root / "manifest.json")
    except Exception as exc:
        manifest = {}
        errors.append(f"manifest.json is malformed: {exc}")
    entries = _manifest_files(manifest, errors)
    schema_version = manifest.get("schema_version") if isinstance(manifest, dict) else None
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"Unsupported Case Pack schema version: {schema_version!r}; expected {SUPPORTED_SCHEMA_VERSION!r}.")
    manifest_paths: set[str] = set()
    for entry in entries:
        relative = entry["path"].replace("\\", "/")
        if not _validate_relative_path(relative):
            errors.append(f"Unsafe manifest path: {relative}.")
            continue
        if relative in manifest_paths:
            errors.append(f"Duplicate manifest path: {relative}.")
        manifest_paths.add(relative)
        path = root / relative
        if not path.is_file():
            errors.append(f"Manifest file is missing: {relative}.")
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        file_hashes[relative] = digest
        if entry.get("bytes") is not None and int(entry["bytes"]) != path.stat().st_size:
            if relative == "manifest.json":
                warnings.append("manifest.json reports a stale self-referential byte count; content hashes for other files are still checked.")
            else:
                errors.append(f"Manifest byte count does not match: {relative}.")
        if entry.get("sha256") and entry["sha256"] != digest:
            errors.append(f"Manifest SHA-256 does not match: {relative}.")
    case_raw: dict[str, Any] = {}
    try:
        case_raw = _json(root / "case.json")
        case_id = case_raw.get("case_id") if isinstance(case_raw, dict) else None
        if not isinstance(case_id, str) or not _safe_case_id(case_id):
            errors.append("case.json must contain a safe case_id using lowercase letters, numbers, '_' or '-'.")
        if isinstance(case_raw, dict) and case_raw.get("schema_version") != schema_version:
            errors.append("case.json schema_version must match manifest.json.")
    except Exception as exc:
        errors.append(f"case.json is malformed: {exc}")
    if isinstance(manifest, dict) and manifest.get("case_id") and case_id and manifest.get("case_id") != case_id:
        errors.append("manifest.json case_id must match case.json case_id.")
    parsed: dict[str, Any] = {}
    for filename in ("timeline.json", "predictions.json", "consequence_graph.json", "sources.json", "portfolio_learning.json"):
        try:
            parsed[filename] = _json(root / filename)
        except Exception as exc:
            errors.append(f"{filename} is malformed: {exc}")
    prediction_items = parsed.get("predictions.json", {})
    prediction_items = prediction_items.get("tests", []) if isinstance(prediction_items, dict) else prediction_items
    if not isinstance(prediction_items, list):
        errors.append("predictions.json must contain a tests array or a list of prediction questions.")
    else:
        for index, prediction in enumerate(prediction_items):
            if not isinstance(prediction, dict):
                errors.append(f"Prediction question {index + 1} must be an object.")
                continue
            try:
                if prediction.get("analytical_support") is not None:
                    validate_analytical_support(prediction["analytical_support"])
                question = PredictionQuestion.model_validate(prediction)
            except Exception as exc:
                prediction_id = prediction.get("prediction_id", index + 1)
                errors.append(f"Prediction {prediction_id} is invalid: {exc}")
    source_items = _source_registry(parsed.get("sources.json"))
    source_ids = {item.get("source_id") for item in source_items if isinstance(item.get("source_id"), str)}
    if len(source_ids) != len(source_items):
        errors.append("sources.json entries must have unique source_id values.")
    refs: set[str] = set()
    for filename, raw in parsed.items():
        if filename != "sources.json":
            refs.update(_source_ids(raw))
    try:
        indicator_frame = pd.read_csv(root / "indicators.csv")
        indicator_ids = set(indicator_frame.get("indicator_id", pd.Series(dtype=str)).dropna().astype(str))
        indicator_sources = set(indicator_frame.get("source_id", pd.Series(dtype=str)).dropna().astype(str))
        refs.update(indicator_sources)
    except Exception as exc:
        indicator_ids = set()
        errors.append(f"indicators.csv is malformed: {exc}")
    missing_sources = sorted(ref for ref in refs if ref not in source_ids)
    if missing_sources:
        errors.append(f"Unresolved source references: {', '.join(missing_sources)}.")
    case_indicator_ids = set(case_raw.get("indicator_ids", [])) if isinstance(case_raw, dict) else set()
    missing_observations = case_indicator_ids - indicator_ids
    if missing_observations:
        warnings.append(f"Case indicators without observations in indicators.csv: {', '.join(sorted(missing_observations))}.")
    for indicator_id in case_indicator_ids:
        try:
            get_indicator_definition(indicator_id)
        except ValueError:
            errors.append(f"Indicator not found: {indicator_id}")
    formula_refs = _formula_refs(root, case_raw if isinstance(case_raw, dict) else {}, warnings, errors)
    unlisted = sorted(present - manifest_paths)
    if unlisted:
        warnings.append(f"Files present but not listed in manifest.json: {', '.join(unlisted)}.")
    graph = parsed.get("consequence_graph.json")
    if isinstance(graph, dict):
        node_ids = {node.get("id") for node in graph.get("nodes", []) if isinstance(node, dict)}
        bad_edges = [f"{edge.get('from')} -> {edge.get('to')}" for edge in graph.get("edges", []) if isinstance(edge, dict) and (edge.get("from") not in node_ids or edge.get("to") not in node_ids)]
        if bad_edges:
            errors.append(f"Consequence graph contains edges with unknown nodes: {', '.join(bad_edges)}.")
    try:
        normalized = _normalize_case(root, origin) if not errors else None
    except Exception as exc:
        normalized = None
        errors.append(f"Case Pack could not be normalized: {exc}")
    if normalized is not None:
        normalized.formula_refs = formula_refs
    report = CasePackValidation(
        valid=not errors,
        case_id=case_id,
        schema_version=schema_version,
        files=sorted(present),
        file_hashes=file_hashes,
        errors=errors,
        warnings=warnings,
        case=normalized.model_dump() if normalized and not errors else None,
    )
    return report, normalized


def _extract_zip(content: bytes, destination: Path) -> Path:
    if not content:
        raise ValueError("The Case Pack ZIP is empty.")
    with zipfile.ZipFile(BytesIO(content)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise ValueError("Case Pack contains too many files.")
        total = 0
        seen: set[str] = set()
        for info in infos:
            name = info.filename.replace("\\", "/")
            if not _validate_relative_path(name.rstrip("/")):
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
            if name in seen:
                raise ValueError(f"Duplicate ZIP path: {name}")
            seen.add(name)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"ZIP symlinks are not allowed: {name}")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Case Pack is too large after decompression.")
        for info in infos:
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    return _find_pack_root(destination)


def _compatibility_case_id(case_id: Any) -> str:
    """Create the stable lowercase id required by the stored Case Pack contract."""
    normalized = re.sub(r"[^a-z0-9_-]+", "_", str(case_id).lower()).strip("_")
    if not _safe_case_id(normalized):
        raise ValueError("The Case Pack case_id cannot be normalized to a safe identifier.")
    return normalized


def _normalize_legacy_case_pack(root: Path) -> bool:
    """Adapt common ChatGPT-exported v1 aliases before strict validation.

    The adapter only changes the temporary extracted copy. Uploaded files on the
    user's machine are never modified, and the normalized copy is validated and
    stored with the same strict contract as built-in packs.
    """
    manifest_path = root / "manifest.json"
    case_path = root / "case.json"
    if not manifest_path.exists() or not case_path.exists():
        return False

    manifest = _json(manifest_path)
    case_raw = _json(case_path)
    compatibility_applied = False
    if not isinstance(manifest, dict) or not isinstance(case_raw, dict):
        return False

    legacy_schema = manifest.get("case_pack_schema_version") or case_raw.get("case_pack_schema_version")
    if legacy_schema is not None and legacy_schema != SUPPORTED_SCHEMA_VERSION:
        return False

    if "schema_version" not in manifest and manifest.get("case_pack_schema_version"):
        manifest["schema_version"] = manifest["case_pack_schema_version"]
        compatibility_applied = True
    if "schema_version" not in case_raw and case_raw.get("case_pack_schema_version"):
        case_raw["schema_version"] = case_raw["case_pack_schema_version"]
        compatibility_applied = True

    original_case_id = case_raw.get("case_id") or manifest.get("case_id")
    normalized_case_id = _compatibility_case_id(original_case_id)
    if case_raw.get("case_id") != normalized_case_id:
        case_raw["case_id"] = normalized_case_id
        compatibility_applied = True
    if manifest.get("case_id") != normalized_case_id:
        manifest["case_id"] = normalized_case_id
        compatibility_applied = True

    trigger = case_raw.get("trigger")
    if isinstance(trigger, str):
        case_raw["trigger"] = {
            "date": case_raw.get("anchor_event_date"),
            "description": trigger,
            "source_ids": [],
        }
        compatibility_applied = True

    artifacts = case_raw.get("artifacts")
    if isinstance(artifacts, list):
        normalized_artifacts = {
            Path(str(item)).stem or "artifact": str(item)
            for item in artifacts
            if isinstance(item, str)
        }
        if normalized_artifacts != artifacts:
            case_raw["artifacts"] = normalized_artifacts
            compatibility_applied = True

    datasets = case_raw.get("datasets")
    if isinstance(datasets, list):
        normalized_datasets = [
            {"path": item, "kind": "market_series"} if isinstance(item, str) else item
            for item in datasets
        ]
        if normalized_datasets != datasets:
            case_raw["datasets"] = normalized_datasets
            compatibility_applied = True

    predictions_path = root / "predictions.json"
    predictions_raw = _json(predictions_path) if predictions_path.exists() else None
    prediction_items = predictions_raw.get("tests", []) if isinstance(predictions_raw, dict) else predictions_raw
    if isinstance(prediction_items, list):
        normalized_predictions: list[dict[str, Any]] = []
        predictions_changed = False
        for prediction in prediction_items:
            if not isinstance(prediction, dict):
                normalized_predictions.append(prediction)
                continue
            normalized_prediction = dict(prediction)
            if "prompt" not in normalized_prediction and "question" in normalized_prediction:
                normalized_prediction["prompt"] = normalized_prediction["question"]
                compatibility_applied = True
                predictions_changed = True
            if "type" not in normalized_prediction and "question_type" in normalized_prediction:
                normalized_prediction["type"] = normalized_prediction["question_type"]
                compatibility_applied = True
                predictions_changed = True
            if "expected_answer" not in normalized_prediction and "expected_view" in normalized_prediction:
                normalized_prediction["expected_answer"] = normalized_prediction["expected_view"]
                compatibility_applied = True
                predictions_changed = True
            if normalized_prediction.get("type") == "binary" and not normalized_prediction.get("options"):
                normalized_prediction["options"] = ["yes", "no", "uncertain"]
                compatibility_applied = True
                predictions_changed = True
            normalized_predictions.append(normalized_prediction)
        if predictions_changed:
            predictions_payload = {"tests": normalized_predictions} if isinstance(predictions_raw, dict) else normalized_predictions
            predictions_path.write_text(json.dumps(predictions_payload, indent=2), encoding="utf-8")

    formula_path = root / "formula_refs.json"
    if formula_path.exists():
        formula_raw = _json(formula_path)
        formula_items = formula_raw.get("formula_refs", formula_raw.get("formulas", [])) if isinstance(formula_raw, dict) else formula_raw
        if isinstance(formula_items, list) and any(isinstance(item, dict) for item in formula_items):
            formula_ids = [
                item.get("formula_id") if isinstance(item, dict) else item
                for item in formula_items
            ]
            formula_raw = {"schema_version": SUPPORTED_SCHEMA_VERSION, "case_id": normalized_case_id, "formula_refs": formula_ids}
            formula_path.write_text(json.dumps(formula_raw, indent=2), encoding="utf-8")
            case_raw["formula_refs"] = formula_ids
            compatibility_applied = True

    if not (root / "indicators.csv").exists() and (root / "market_series").exists():
        series_rows: list[dict[str, Any]] = []
        for series_path in sorted((root / "market_series").glob("*.csv")):
            series_rows.extend(_normalize_market_series(series_path))
        indicator_rows = [
            {
                "indicator_id": row.get("indicator_id"),
                "dimension": "market",
                "label": row.get("label"),
                "date": row.get("date"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "direction": "",
                "evidence_type": row.get("data_status", "OBSERVED"),
                "source_id": row.get("source_id"),
                "note": "Generated from market_series for compatibility with Case Pack schema v1.",
            }
            for row in series_rows
        ]
        pd.DataFrame(indicator_rows).to_csv(root / "indicators.csv", index=False)
        compatibility_applied = True

    if not compatibility_applied:
        return False

    if case_raw.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        case_raw["schema_version"] = SUPPORTED_SCHEMA_VERSION
    manifest["schema_version"] = SUPPORTED_SCHEMA_VERSION
    case_path.write_text(json.dumps(case_raw, indent=2), encoding="utf-8")

    # Rebuild the extracted manifest after alias conversion and generated indicators.
    # Content hashes are intentionally omitted here; strict validation still checks
    # every listed file and the original upload remains untouched.
    files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest["files"] = [{"path": path} for path in files] + [{"path": "manifest.json"}]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return True


def import_case_pack(content: bytes) -> ResearchCaseImportResponse:
    IMPORTED_ROOT.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="case-pack-", dir=IMPORTED_ROOT))
    try:
        root = _extract_zip(content, staging)
        compatibility_applied = _normalize_legacy_case_pack(root)
        report, case = validate_case_pack_directory(root)
        if compatibility_applied:
            report.warnings.insert(0, "Applied compatibility normalization for a legacy ChatGPT Case Pack export.")
        if not report.valid or case is None:
            report.imported = False
            return ResearchCaseImportResponse(**report.model_dump())
        destination = IMPORTED_ROOT / case.case_id
        lock_path = IMPORTED_ROOT / f".{case.case_id}.import.lock"
        try:
            lock = lock_path.open("x")
        except FileExistsError as exc:
            raise ValueError("This case is already being imported; existing data was preserved.") from exc
        try:
            with lock:
                if destination.exists() or destination.is_symlink():
                    raise ValueError("This case ID is already imported. Use a new case ID; existing data was preserved.")
                # Staging and destination share a filesystem; rename publishes the
                # validated pack atomically without deleting an older import.
                root.rename(destination)
        finally:
            lock_path.unlink()
        report.imported = True
        return ResearchCaseImportResponse(
            **report.model_dump(),
            case_summary=_summary(case, destination, "imported"),
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _case_directories() -> list[tuple[Path, str]]:
    directories: list[tuple[Path, str]] = []
    for root, origin in ((BUILT_IN_ROOT, "built_in"), (IMPORTED_ROOT, "imported")):
        if not root.exists():
            continue
        for manifest in sorted(root.glob("*/manifest.json")):
            directories.append((manifest.parent, origin))
    return directories


def list_research_cases() -> list[ResearchCaseSummary]:
    result: list[ResearchCaseSummary] = []
    for root, origin in _case_directories():
        report, case = validate_case_pack_directory(root, origin)
        if report.valid and case is not None:
            result.append(_summary(case, root, origin))
    # Keep the original golden case as the default while allowing all imported
    # and built-in cases to remain available in a stable alphabetical order.
    result.sort(key=lambda item: (item.case_id != "uk_2022_mini_budget_ldi", item.short_title.lower()))
    return result


def get_research_case(case_id: str) -> ResearchCase:
    for root, origin in _case_directories():
        if root.name != case_id:
            continue
        report, case = validate_case_pack_directory(root, origin)
        if not report.valid or case is None:
            raise ValueError("The stored Research Case failed validation: " + "; ".join(report.errors))
        return case
    raise ValueError(f"Research Case not found: {case_id}")


def case_artifact_path(case_id: str, artifact_path: str) -> Path:
    if not _safe_case_id(case_id) or not _validate_relative_path(artifact_path):
        raise ValueError("Invalid Research Case artifact path.")
    for root, _ in _case_directories():
        if root.name == case_id:
            candidate = (root / artifact_path).resolve()
            if root.resolve() not in candidate.parents or not candidate.is_file():
                break
            return candidate
    raise ValueError("Research Case artifact not found.")
