from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json

import httpx

import pandas as pd

from app.models.schemas import (
    DatasetMetadata,
    DatasetPreview,
    ImfCountry,
    ImfCountryCatalog,
    ImfFetchRequest,
    ImfFetchResponse,
    ImfPrefetchAllRequest,
    ImfPrefetchedSessionRequest,
)
from app.services.cache_service import cache_key, read_cache, write_cache
from app.services.data_transform_service import COUNTRY_CODES, imf_learning_notes, transform_datamapper_payloads
from app.services.dataset_registry_service import (
    REGISTRY_DIR,
    load_dataset,
    metadata_from_csv,
    preview_from_metadata,
    upsert_dataset,
)
from app.services.indicator_mapping_service import load_indicator_mapping


DATAMAPPER_BASES = [
    "https://www.imf.org/external/datamapper/api/v1",
    "https://www.imf.org/external/datamapper/api/v2",
]
DATAMAPPER_COUNTRIES_URL = f"{DATAMAPPER_BASES[0]}/countries"
COUNTRIES_CACHE_KEY = cache_key(["imf", "datamapper", "countries"])
COUNTRY_CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "imf_country_catalog.json"

PROGRESS_STATES = [
    "Connecting to IMF API...",
    "Fetching country catalogue...",
    "Fetching indicator data...",
    "Transforming data into country-year panel...",
    "Checking missing values...",
    "Dataset ready.",
]

ALL_COUNTRIES_PREFETCH_NOTE = "IMF_ALL_COUNTRIES_PREFETCH"
PREFETCHED_SESSION_NOTE = "IMF_PREFETCHED_TEST_SESSION"
PREFETCH_CHUNK_SIZE = 50


def _fallback_countries() -> list[ImfCountry]:
    return sorted(
        [ImfCountry(name=name, code=code) for name, code in COUNTRY_CODES.items()],
        key=lambda country: country.name.casefold(),
    )


def parse_country_catalog(payload: dict[str, Any]) -> list[ImfCountry]:
    raw_countries = payload.get("countries", {})
    if not isinstance(raw_countries, dict):
        return []
    countries: list[ImfCountry] = []
    seen_codes: set[str] = set()
    for code, details in raw_countries.items():
        if not isinstance(code, str) or len(code.strip()) != 3:
            continue
        label = details.get("label") if isinstance(details, dict) else None
        if not isinstance(label, str) or not label.strip():
            continue
        normalized_code = code.strip().upper()
        if normalized_code in seen_codes:
            continue
        seen_codes.add(normalized_code)
        countries.append(ImfCountry(code=normalized_code, name=label.strip()))
    return sorted(countries, key=lambda country: (country.name.casefold(), country.code))


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _country_catalog_payload(countries: list[ImfCountry], last_modified_utc: str | None) -> ImfCountryCatalog:
    return ImfCountryCatalog(
        source_url=DATAMAPPER_COUNTRIES_URL,
        last_modified_utc=last_modified_utc,
        country_count=len(countries),
        countries=countries,
    )


def write_static_country_catalog(payload: dict[str, Any], last_modified_utc: str | None = None) -> ImfCountryCatalog:
    countries = parse_country_catalog(payload)
    if not countries:
        raise ValueError("IMF country catalogue response did not include labelled countries.")

    catalog = _country_catalog_payload(countries, last_modified_utc or _utc_now())
    COUNTRY_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    COUNTRY_CATALOG_PATH.write_text(catalog.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return catalog


def country_catalog() -> ImfCountryCatalog:
    if COUNTRY_CATALOG_PATH.exists():
        catalog = ImfCountryCatalog(**json.loads(COUNTRY_CATALOG_PATH.read_text(encoding="utf-8")))
        if catalog.countries:
            return catalog

    cached = read_cache(COUNTRIES_CACHE_KEY)
    if cached:
        countries = parse_country_catalog(cached)
        if countries:
            return _country_catalog_payload(countries, None)
    return _country_catalog_payload(_fallback_countries(), None)


def refresh_country_catalog() -> ImfCountryCatalog:
    with httpx.Client(timeout=15.0) as client:
        payload = _fetch_json_sync(client, DATAMAPPER_COUNTRIES_URL)
    write_cache(COUNTRIES_CACHE_KEY, payload)
    return write_static_country_catalog(payload)


def supported_countries() -> list[ImfCountry]:
    return country_catalog().countries


async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def _fetch_json_sync(client: httpx.Client, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def fetch_indicator_payload(
    client: httpx.AsyncClient,
    indicator_code: str,
    country_codes: list[str],
    years: list[int],
) -> dict[str, Any]:
    cache = cache_key([indicator_code, ",".join(country_codes), ",".join(str(year) for year in years)])
    cached = read_cache(cache)
    if cached is not None:
        return cached

    periods = ",".join(str(year) for year in years)
    country_path = "/".join(country_codes)
    last_error: Exception | None = None
    for base in DATAMAPPER_BASES:
        url = f"{base}/{indicator_code}/{country_path}"
        try:
            payload = await _fetch_json(client, url, {"periods": periods})
            write_cache(cache, payload)
            return payload
        except Exception as exc:  # pragma: no cover - exercised with mocked failures
            last_error = exc
    raise RuntimeError("Could not fetch IMF data at the moment. You can still continue with sample datasets or upload a CSV.") from last_error


async def fetch_indicator_all_countries_payload(
    client: httpx.AsyncClient,
    indicator_code: str,
    years: list[int],
) -> dict[str, Any]:
    cache = cache_key([indicator_code, "all_countries", ",".join(str(year) for year in years)])
    cached = read_cache(cache)
    if cached is not None:
        return cached

    periods = ",".join(str(year) for year in years)
    last_error: Exception | None = None
    for base in DATAMAPPER_BASES:
        url = f"{base}/{indicator_code}"
        try:
            payload = await _fetch_json(client, url, {"periods": periods})
            write_cache(cache, payload)
            return payload
        except Exception as exc:  # pragma: no cover - exercised with mocked failures
            last_error = exc
    raise RuntimeError("Could not fetch IMF all-country data at the moment.") from last_error


def _extract_indicator_values(payload: dict[str, Any], indicator_code: str) -> dict[str, Any]:
    values = payload.get("values", payload)
    if isinstance(values, dict) and indicator_code in values and isinstance(values[indicator_code], dict):
        return values[indicator_code]
    return values if isinstance(values, dict) else {}


def _merge_indicator_payload(target: dict[str, Any], incoming: dict[str, Any], indicator_code: str) -> None:
    target_values = target.setdefault("values", {}).setdefault(indicator_code, {})
    target_values.update(_extract_indicator_values(incoming, indicator_code))


async def fetch_indicator_payload_chunked(
    client: httpx.AsyncClient,
    indicator_code: str,
    country_codes: list[str],
    years: list[int],
    chunk_size: int = PREFETCH_CHUNK_SIZE,
) -> dict[str, Any]:
    merged: dict[str, Any] = {"values": {indicator_code: {}}}
    failed_codes: list[str] = []

    for index in range(0, len(country_codes), chunk_size):
        chunk = country_codes[index : index + chunk_size]
        try:
            payload = await fetch_indicator_payload(client, indicator_code, chunk, years)
            _merge_indicator_payload(merged, payload, indicator_code)
            continue
        except Exception:
            pass

        for code in chunk:
            try:
                payload = await fetch_indicator_payload(client, indicator_code, [code], years)
                _merge_indicator_payload(merged, payload, indicator_code)
            except Exception:
                failed_codes.append(code)

    if failed_codes:
        merged["warnings"] = {indicator_code: {"failed_country_codes": failed_codes}}
    return merged


def _validate_indicator_selection(indicator_codes: list[str]) -> tuple[dict[str, Any], list[str]]:
    indicators = load_indicator_mapping()
    selected = indicator_codes or list(indicators)
    unknown = [code for code in selected if code not in indicators]
    if unknown:
        raise ValueError(f"Unsupported IMF indicators: {', '.join(unknown)}")
    return indicators, selected


def _catalog_mappings() -> tuple[ImfCountryCatalog, dict[str, str], dict[str, str]]:
    catalog = country_catalog()
    country_names_by_code = {country.code: country.name for country in catalog.countries}
    country_codes_by_name = {country.name: country.code for country in catalog.countries}
    return catalog, country_names_by_code, country_codes_by_name


def _write_imf_dataset(
    dataset_id: str,
    name: str,
    df: pd.DataFrame,
    metadata_payload: dict[str, Any],
    notes: list[str],
) -> ImfFetchResponse:
    target = REGISTRY_DIR / "generated" / f"{dataset_id}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)

    metadata = metadata_from_csv(
        dataset_id=dataset_id,
        name=name,
        source_type="imf_api",
        source_name="IMF DataMapper",
        file_path=Path(target),
        notes=notes,
    )
    metadata.frequency = "annual"
    metadata_path = REGISTRY_DIR / "generated" / f"{dataset_id}.meta.json"
    metadata.metadata_path = str(metadata_path)
    metadata_path.write_text(json.dumps(metadata_payload, indent=2) + "\n", encoding="utf-8")
    upsert_dataset(metadata)

    return ImfFetchResponse(
        dataset=metadata,
        preview=DatasetPreview(**preview_from_metadata(metadata)),
        progress_states=PROGRESS_STATES,
    )


async def fetch_imf_dataset(request: ImfFetchRequest) -> ImfFetchResponse:
    indicators, selected_indicators = _validate_indicator_selection(request.indicators)
    years = list(range(request.start_year, request.end_year + 1))
    catalog, country_names_by_code, country_codes_by_name = _catalog_mappings()
    country_codes = [country_codes_by_name.get(country, country) for country in request.countries]
    payloads: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for indicator_code in selected_indicators:
            payloads[indicator_code] = await fetch_indicator_payload(client, indicator_code, country_codes, years)

    df = transform_datamapper_payloads(
        payloads,
        indicators,
        request.countries,
        years,
        country_names_by_code=country_names_by_code,
        country_codes_by_name=country_codes_by_name,
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dataset_id = f"imf_fetch_{timestamp}"
    return _write_imf_dataset(
        dataset_id=dataset_id,
        name=f"IMF Fetch - {len(request.countries)} Countries, {len(request.indicators)} Indicators, {request.start_year}-{request.end_year}",
        df=df,
        metadata_payload={
            "source": "IMF DataMapper",
            "countries": request.countries,
            "country_codes": country_codes,
            "country_catalog_last_modified_utc": catalog.last_modified_utc,
            "indicators": [indicators[code].model_dump() for code in selected_indicators],
            "date_range": f"{request.start_year} to {request.end_year}",
            "notes": imf_learning_notes(),
        },
        notes=imf_learning_notes(),
    )


async def prefetch_all_countries_dataset(request: ImfPrefetchAllRequest) -> ImfFetchResponse:
    indicators, selected_indicators = _validate_indicator_selection(request.indicators)
    years = list(range(request.start_year, request.end_year + 1))
    catalog, country_names_by_code, country_codes_by_name = _catalog_mappings()
    country_codes = [country.code for country in catalog.countries]
    payloads: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for indicator_code in selected_indicators:
            try:
                payloads[indicator_code] = await fetch_indicator_all_countries_payload(client, indicator_code, years)
            except Exception:
                payloads[indicator_code] = await fetch_indicator_payload_chunked(client, indicator_code, country_codes, years)

    df = transform_datamapper_payloads(
        payloads,
        indicators,
        country_codes,
        years,
        country_names_by_code=country_names_by_code,
        country_codes_by_name=country_codes_by_name,
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dataset_id = f"imf_all_countries_{timestamp}"
    notes = [
        ALL_COUNTRIES_PREFETCH_NOTE,
        f"Prefetched all {catalog.country_count} labelled IMF countries from the static country catalogue.",
        f"Country catalogue last modified: {catalog.last_modified_utc or 'unknown'}.",
        *imf_learning_notes(),
    ]
    return _write_imf_dataset(
        dataset_id=dataset_id,
        name=f"IMF Prefetch - All Countries, {len(selected_indicators)} Indicators, {request.start_year}-{request.end_year}",
        df=df,
        metadata_payload={
            "source": "IMF DataMapper",
            "prefetch_type": "all_countries",
            "country_count": catalog.country_count,
            "country_codes": country_codes,
            "country_catalog_last_modified_utc": catalog.last_modified_utc,
            "indicators": [indicators[code].model_dump() for code in selected_indicators],
            "date_range": f"{request.start_year} to {request.end_year}",
            "notes": notes,
        },
        notes=notes,
    )


def create_prefetched_test_session(request: ImfPrefetchedSessionRequest) -> ImfFetchResponse:
    indicators, selected_indicators = _validate_indicator_selection(request.indicators)
    catalog, country_names_by_code, country_codes_by_name = _catalog_mappings()
    metadata, df = load_dataset(request.source_dataset_id)
    selected_codes = [country_codes_by_name.get(country, country) for country in request.countries]
    if "country_code" not in df.columns:
        raise ValueError("Selected source dataset does not include country_code and cannot be used as a prefetched IMF source.")
    session_df = df[df["country_code"].astype(str).isin(selected_codes)].copy()
    if request.start_year is not None:
        session_df = session_df[session_df[metadata.date_column].astype(str) >= str(request.start_year)]
    if request.end_year is not None:
        session_df = session_df[session_df[metadata.date_column].astype(str) <= str(request.end_year)]

    indicator_columns = [indicators[code].platform_variable for code in selected_indicators if indicators[code].platform_variable in session_df.columns]
    keep_columns = [column for column in ["country", "country_code", metadata.date_column, *indicator_columns] if column in session_df.columns]
    session_df = session_df[keep_columns].sort_values(["country", metadata.date_column]).reset_index(drop=True)
    if session_df.empty:
        raise ValueError("The selected countries and date range produced no rows from the prefetched dataset.")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dataset_id = f"imf_test_session_{timestamp}"
    notes = [
        PREFETCHED_SESSION_NOTE,
        f"Created from prefetched dataset {request.source_dataset_id}; no live IMF API call was made.",
        *imf_learning_notes(),
    ]
    return _write_imf_dataset(
        dataset_id=dataset_id,
        name=f"IMF Test Session - {len(request.countries)} Countries, {len(indicator_columns)} Variables",
        df=session_df,
        metadata_payload={
            "source": "Prefetched IMF DataMapper dataset",
            "source_dataset_id": request.source_dataset_id,
            "countries": request.countries,
            "country_codes": selected_codes,
            "country_catalog_last_modified_utc": catalog.last_modified_utc,
            "indicators": [indicators[code].model_dump() for code in selected_indicators],
            "date_range": f"{request.start_year or metadata.date_range} to {request.end_year or metadata.date_range}",
            "notes": notes,
        },
        notes=notes,
    )
