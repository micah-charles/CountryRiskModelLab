from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json
import sqlite3

import pandas as pd

from app.config.settings import get_settings
from app.models.schemas import DatasetMetadata


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
REGISTRY_DIR = APP_DIR / "data_registry"
REGISTRY_PATH = REGISTRY_DIR / "registry.json"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_registry() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    (REGISTRY_DIR / "uploaded").mkdir(exist_ok=True)
    (REGISTRY_DIR / "generated").mkdir(exist_ok=True)
    (REGISTRY_DIR / "imf_cache").mkdir(exist_ok=True)
    if _registry_backend() == "sqlite":
        _ensure_sqlite_registry()
    elif not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text("[]\n", encoding="utf-8")


def _registry_backend() -> str:
    backend = get_settings().dataset_registry_backend
    if backend not in {"json", "sqlite"}:
        raise ValueError(f"Unsupported DATASET_REGISTRY_BACKEND: {backend}")
    return backend


def _sqlite_path() -> Path:
    return get_settings().dataset_registry_sqlite_path


def _ensure_sqlite_registry() -> None:
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _read_sqlite_registry() -> list[DatasetMetadata]:
    _ensure_sqlite_registry()
    with sqlite3.connect(_sqlite_path()) as connection:
        rows = connection.execute("SELECT payload FROM datasets ORDER BY dataset_id").fetchall()
    return [DatasetMetadata(**json.loads(row[0])) for row in rows]


def _write_sqlite_registry(items: list[DatasetMetadata]) -> None:
    _ensure_sqlite_registry()
    with sqlite3.connect(_sqlite_path()) as connection:
        connection.execute("DELETE FROM datasets")
        connection.executemany(
            "INSERT INTO datasets(dataset_id, payload, updated_at) VALUES (?, ?, ?)",
            [
                (
                    item.dataset_id,
                    json.dumps(item.model_dump(), sort_keys=True),
                    utc_now(),
                )
                for item in items
            ],
        )
        connection.commit()


def _upsert_sqlite_dataset(metadata: DatasetMetadata) -> DatasetMetadata:
    _ensure_sqlite_registry()
    with sqlite3.connect(_sqlite_path()) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO datasets(dataset_id, payload, updated_at) VALUES (?, ?, ?)",
            (metadata.dataset_id, json.dumps(metadata.model_dump(), sort_keys=True), utc_now()),
        )
        connection.commit()
    return metadata


def read_registry() -> list[DatasetMetadata]:
    ensure_registry()
    if _registry_backend() == "sqlite":
        return _read_sqlite_registry()
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [DatasetMetadata(**item) for item in raw]


def write_registry(items: list[DatasetMetadata]) -> None:
    ensure_registry()
    if _registry_backend() == "sqlite":
        _write_sqlite_registry(items)
        return
    payload = [item.model_dump() for item in items]
    REGISTRY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def upsert_dataset(metadata: DatasetMetadata) -> DatasetMetadata:
    if _registry_backend() == "sqlite":
        return _upsert_sqlite_dataset(metadata)
    items = [item for item in read_registry() if item.dataset_id != metadata.dataset_id]
    items.append(metadata)
    write_registry(items)
    return metadata


def get_dataset(dataset_id: str) -> DatasetMetadata:
    for item in read_registry():
        if item.dataset_id == dataset_id:
            return item
    raise ValueError(f"Dataset not found: {dataset_id}")


def detect_frequency(date_values: pd.Series) -> str:
    values = date_values.dropna().astype(str)
    if values.empty:
        return "unknown"
    sample = values.iloc[0]
    if "-Q" in sample:
        return "quarterly"
    if len(sample) == 7 and sample[4] == "-":
        return "monthly"
    if len(sample) == 4 and sample.isdigit():
        return "annual"
    return "unknown"


def infer_date_range(df: pd.DataFrame, date_column: str) -> str | None:
    if date_column not in df.columns or df.empty:
        return None
    values = df[date_column].dropna().astype(str).sort_values()
    if values.empty:
        return None
    return f"{values.iloc[0]} to {values.iloc[-1]}"


def metadata_from_csv(
    dataset_id: str,
    name: str,
    source_type: str,
    source_name: str,
    file_path: Path,
    country_column: str = "country",
    date_column: str = "date",
    notes: list[str] | None = None,
    created_at: str | None = None,
) -> DatasetMetadata:
    df = pd.read_csv(file_path)
    countries = sorted(df[country_column].dropna().astype(str).unique().tolist()) if country_column in df.columns else []
    return DatasetMetadata(
        dataset_id=dataset_id,
        name=name,
        source_type=source_type,  # type: ignore[arg-type]
        source_name=source_name,
        created_at=created_at or utc_now(),
        frequency=detect_frequency(df[date_column]) if date_column in df.columns else "unknown",
        country_column=country_column,
        date_column=date_column,
        columns=list(df.columns),
        file_path=str(file_path),
        metadata_path=None,
        countries=countries,
        date_range=infer_date_range(df, date_column),
        notes=notes or [],
    )


def register_sample_datasets() -> None:
    existing = {item.dataset_id for item in read_registry()}
    samples = [
        {
            "dataset_id": "sample_country_risk_quarterly",
            "name": "Sample Country Risk Quarterly Dataset",
            "source_type": "sample",
            "source_name": "Synthetic sample data",
            "path": DATA_DIR / "sample_country_risk_quarterly.csv",
        },
        {
            "dataset_id": "sample_country_risk_monthly",
            "name": "Sample Country Risk Monthly Dataset",
            "source_type": "sample",
            "source_name": "Synthetic sample data",
            "path": DATA_DIR / "sample_country_risk_monthly.csv",
        },
        {
            "dataset_id": "imf_all_countries_2010_2026",
            "name": "IMF Static - All Countries, Annual Macro (2010-2026)",
            "source_type": "imf_api",
            "source_name": "IMF DataMapper static seed",
            "path": DATA_DIR / "imf_all_countries_2010_2026.csv",
            "created_at": "2026-07-04T14:44:41Z",
            "notes": [
                "Static seed generated from IMF DataMapper on 2026-07-04.",
                "Country catalogue last modified: 2026-07-04T14:28:10Z.",
                "This dataset covers all 239 labelled IMF DataMapper countries in the bundled catalogue for 2010-2026.",
                "Refresh live IMF data with scripts/prefetch_imf_all_countries_dataset.py when an updated runtime dataset is needed.",
            ],
        },
    ]
    for dataset in samples:
        dataset_id = dataset["dataset_id"]
        path = dataset["path"]
        if path.exists() and dataset_id not in existing:
            upsert_dataset(
                metadata_from_csv(
                    dataset_id,
                    dataset["name"],
                    dataset["source_type"],
                    dataset["source_name"],
                    path,
                    notes=dataset.get("notes"),
                    created_at=dataset.get("created_at"),
                )
            )


def list_datasets(source_type: str | None = None) -> list[DatasetMetadata]:
    register_sample_datasets()
    items = read_registry()
    if source_type:
        return [item for item in items if item.source_type == source_type]
    return items


def load_dataset(dataset_id: str) -> tuple[DatasetMetadata, pd.DataFrame]:
    register_sample_datasets()
    metadata = get_dataset(dataset_id)
    path = Path(metadata.file_path)
    if not path.is_absolute():
        path = APP_DIR / path
    if not path.exists():
        raise ValueError(f"Dataset file not found: {metadata.file_path}")
    return metadata, pd.read_csv(path)


def model_numeric_columns(df: pd.DataFrame, country_column: str = "country", date_column: str = "date") -> list[str]:
    identifier_columns = {
        country_column,
        date_column,
        "country",
        "country_code",
        "iso2",
        "iso3",
        "iso_code",
        "id",
        "date",
        "year",
    }
    identifier_names = {column.lower() for column in identifier_columns if column}
    return [
        column
        for column in df.select_dtypes(include="number").columns.tolist()
        if column.lower() not in identifier_names
    ]


def preview_from_metadata(metadata: DatasetMetadata, limit: int = 20) -> dict[str, Any]:
    path = Path(metadata.file_path)
    if not path.is_absolute():
        path = APP_DIR / path
    df = pd.read_csv(path)
    numeric_columns = model_numeric_columns(df, metadata.country_column, metadata.date_column)
    return {
        "dataset_id": metadata.dataset_id,
        "name": metadata.name,
        "source_type": metadata.source_type,
        "source_name": metadata.source_name,
        "frequency": metadata.frequency,
        "columns": list(df.columns),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "rows": df.head(limit).replace({pd.NA: None}).where(pd.notnull(df.head(limit)), None).to_dict(orient="records"),
        "numeric_columns": numeric_columns,
        "date_column": metadata.date_column,
        "country_column": metadata.country_column,
        "missing_values": {column: int(count) for column, count in df.isna().sum().items()},
        "countries": metadata.countries,
        "date_range": metadata.date_range,
        "notes": metadata.notes,
    }
