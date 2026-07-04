from app.models.schemas import DatasetMetadata
from app.services.dataset_registry_service import list_datasets, load_dataset, read_registry, register_sample_datasets, upsert_dataset, write_registry


def test_sample_dataset_loads():
    register_sample_datasets()
    datasets = list_datasets("sample")
    ids = {dataset.dataset_id for dataset in datasets}
    assert "sample_country_risk_quarterly" in ids
    assert "sample_country_risk_monthly" in ids


def test_sample_dataset_has_required_country_risk_columns():
    _, df = load_dataset("sample_country_risk_quarterly")
    assert {"country", "date", "bond_yield_10y", "inflation_yoy", "policy_rate"}.issubset(df.columns)


def test_sqlite_registry_backend_reads_and_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("DATASET_REGISTRY_BACKEND", "sqlite")
    monkeypatch.setenv("DATASET_REGISTRY_SQLITE_PATH", str(tmp_path / "registry.sqlite3"))
    metadata = DatasetMetadata(
        dataset_id="sqlite_test_dataset",
        name="SQLite Test Dataset",
        source_type="sample",
        source_name="Test",
        created_at="2026-07-03T00:00:00Z",
        frequency="annual",
        country_column="country",
        date_column="date",
        columns=["country", "date", "value"],
        file_path="/tmp/sqlite-test.csv",
    )

    write_registry([])
    assert read_registry() == []
    upsert_dataset(metadata)
    items = read_registry()
    assert len(items) == 1
    assert items[0].dataset_id == "sqlite_test_dataset"
