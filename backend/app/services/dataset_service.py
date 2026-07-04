from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from fastapi import UploadFile

from app.config.settings import get_settings
from app.models.schemas import DatasetPreview
from app.services.dataset_registry_service import (
    REGISTRY_DIR,
    list_datasets,
    load_dataset,
    metadata_from_csv,
    preview_from_metadata,
    upsert_dataset,
    utc_now,
)


def list_sample_datasets():
    return list_datasets("sample")


def list_all_datasets():
    return list_datasets()


def get_preview(dataset_id: str, limit: int = 20) -> DatasetPreview:
    metadata, _ = load_dataset(dataset_id)
    return DatasetPreview(**preview_from_metadata(metadata, limit=limit))


async def save_uploaded_dataset(file: UploadFile) -> DatasetPreview:
    settings = get_settings()
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", file.filename or "uploaded.csv")
    dataset_id = f"upload_{utc_now().replace(':', '').replace('-', '').replace('Z', '')}_{safe_name.rsplit('.', 1)[0]}"
    target = REGISTRY_DIR / "uploaded" / f"{dataset_id}.csv"
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise ValueError(f"Uploaded CSV exceeds the maximum allowed size of {settings.max_upload_bytes} bytes.")
    target.write_bytes(content)

    df = pd.read_csv(target)
    if "country" not in df.columns or "date" not in df.columns:
        raise ValueError("Uploaded CSV must include country and date columns for MVP modelling.")

    metadata = metadata_from_csv(dataset_id, safe_name, "upload", "Uploaded CSV", Path(target))
    upsert_dataset(metadata)
    return DatasetPreview(**preview_from_metadata(metadata))


def filter_model_frame(
    dataset_id: str,
    country: str | None,
    date_start: str | None,
    date_end: str | None,
    required_columns: list[str],
) -> tuple[object, pd.DataFrame]:
    metadata, df = load_dataset(dataset_id)
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if country and metadata.country_column in df.columns:
        df = df[df[metadata.country_column].astype(str) == country]
    if date_start and metadata.date_column in df.columns:
        df = df[df[metadata.date_column].astype(str) >= date_start]
    if date_end and metadata.date_column in df.columns:
        df = df[df[metadata.date_column].astype(str) <= date_end]
    keep_columns = [metadata.date_column, metadata.country_column] + required_columns
    keep_columns = [column for column in keep_columns if column in df.columns]
    return metadata, df[keep_columns].copy().sort_values(metadata.date_column)
