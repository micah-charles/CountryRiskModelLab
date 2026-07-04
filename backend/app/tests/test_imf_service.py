from pathlib import Path

from app.models.schemas import ImfCountryCatalog, ImfFetchRequest, ImfPrefetchAllRequest, ImfPrefetchedSessionRequest
from app.services.data_transform_service import transform_datamapper_payloads
from app.services.imf_service import (
    create_prefetched_test_session,
    country_catalog,
    fetch_imf_dataset,
    parse_country_catalog,
    prefetch_all_countries_dataset,
    write_static_country_catalog,
)
from app.services.indicator_mapping_service import load_indicator_mapping
from app.services.dataset_registry_service import read_registry, write_registry


def test_indicator_response_parser_converts_api_result_into_tidy_dataframe():
    mapping = load_indicator_mapping()
    payloads = {
        "NGDP_RPCH": {"values": {"NGDP_RPCH": {"IDN": {"2020": "5.0", "2021": "4.8"}}}},
        "PCPIPCH": {"values": {"PCPIPCH": {"IDN": {"2020": "3.0", "2021": "3.4"}}}},
    }
    df = transform_datamapper_payloads(payloads, mapping, ["Indonesia"], [2020, 2021])
    assert list(df.columns) == ["country", "country_code", "date", "gdp_growth_yoy", "inflation_yoy"]
    assert df.loc[0, "country_code"] == "IDN"
    assert df.loc[1, "inflation_yoy"] == 3.4


def test_country_catalog_parser_returns_labelled_imf_countries():
    payload = {
        "countries": {
            "ABW": {"label": "Aruba"},
            "ATI": {"label": None},
            "BRA": {"label": "Brazil"},
            "bad": {"label": ""},
        }
    }

    countries = parse_country_catalog(payload)

    assert [country.model_dump() for country in countries] == [
        {"code": "ABW", "name": "Aruba"},
        {"code": "BRA", "name": "Brazil"},
    ]


def test_static_country_catalog_records_last_modified(monkeypatch, tmp_path):
    import app.services.imf_service as imf_service

    catalog_path = tmp_path / "imf_country_catalog.json"
    monkeypatch.setattr(imf_service, "COUNTRY_CATALOG_PATH", catalog_path)

    payload = {"countries": {"JPN": {"label": "Japan"}, "THA": {"label": "Thailand"}}}
    catalog = write_static_country_catalog(payload, last_modified_utc="2026-07-04T14:30:00Z")
    loaded = country_catalog()

    assert catalog_path.exists()
    assert catalog.last_modified_utc == "2026-07-04T14:30:00Z"
    assert loaded.last_modified_utc == "2026-07-04T14:30:00Z"
    assert [country.code for country in loaded.countries] == ["JPN", "THA"]


async def fake_fetch_indicator_payload(client, indicator_code, country_codes, years):
    return {"values": {indicator_code: {code: {str(year): "1.5" for year in years} for code in country_codes}}}


async def fake_fetch_indicator_all_countries_payload(client, indicator_code, years):
    return {"values": {indicator_code: {code: {str(year): "1.5" for year in years} for code in ["IDN", "THA"]}}}


def test_imf_fetched_dataset_is_saved_into_registry(monkeypatch):
    import app.services.imf_service as imf_service

    monkeypatch.setattr(imf_service, "fetch_indicator_payload", fake_fetch_indicator_payload)
    monkeypatch.setattr(
        imf_service,
        "country_catalog",
        lambda: ImfCountryCatalog(
            source_url="https://example.test/imf/countries",
            last_modified_utc="2026-07-04T14:30:00Z",
            country_count=2,
            countries=[
                imf_service.ImfCountry(code="IDN", name="Indonesia"),
                imf_service.ImfCountry(code="BRA", name="Brazil"),
            ],
        ),
    )
    response = __import__("asyncio").run(
        fetch_imf_dataset(
            ImfFetchRequest(
                countries=["IDN"],
                indicators=["NGDP_RPCH", "PCPIPCH"],
                start_year=2020,
                end_year=2021,
            )
        )
    )
    assert response.dataset.source_type == "imf_api"
    assert Path(response.dataset.file_path).exists()
    assert response.preview.countries == ["Indonesia"]
    assert response.preview.missing_values["gdp_growth_yoy"] == 0

    Path(response.dataset.file_path).unlink(missing_ok=True)
    if response.dataset.metadata_path:
        Path(response.dataset.metadata_path).unlink(missing_ok=True)
    write_registry([item for item in read_registry() if item.dataset_id != response.dataset.dataset_id])


def test_all_country_prefetch_and_session_use_prefetched_data(monkeypatch):
    import asyncio
    import app.services.imf_service as imf_service

    monkeypatch.setattr(imf_service, "fetch_indicator_payload", fake_fetch_indicator_payload)
    monkeypatch.setattr(imf_service, "fetch_indicator_all_countries_payload", fake_fetch_indicator_all_countries_payload)
    monkeypatch.setattr(
        imf_service,
        "country_catalog",
        lambda: ImfCountryCatalog(
            source_url="https://example.test/imf/countries",
            last_modified_utc="2026-07-04T14:30:00Z",
            country_count=2,
            countries=[
                imf_service.ImfCountry(code="IDN", name="Indonesia"),
                imf_service.ImfCountry(code="THA", name="Thailand"),
            ],
        ),
    )

    prefetch = asyncio.run(
        prefetch_all_countries_dataset(
            ImfPrefetchAllRequest(indicators=["NGDP_RPCH", "PCPIPCH"], start_year=2020, end_year=2021)
        )
    )
    session = create_prefetched_test_session(
        ImfPrefetchedSessionRequest(
            source_dataset_id=prefetch.dataset.dataset_id,
            countries=["THA"],
            indicators=["NGDP_RPCH"],
            start_year=2020,
            end_year=2021,
        )
    )

    assert prefetch.dataset.dataset_id.startswith("imf_all_countries_")
    assert set(prefetch.preview.countries) == {"Indonesia", "Thailand"}
    assert session.dataset.dataset_id.startswith("imf_test_session_")
    assert session.preview.countries == ["Thailand"]
    assert session.preview.columns == ["country", "country_code", "date", "gdp_growth_yoy"]

    for response in [prefetch, session]:
        Path(response.dataset.file_path).unlink(missing_ok=True)
        if response.dataset.metadata_path:
            Path(response.dataset.metadata_path).unlink(missing_ok=True)
    remove_ids = {prefetch.dataset.dataset_id, session.dataset.dataset_id}
    write_registry([item for item in read_registry() if item.dataset_id not in remove_ids])
