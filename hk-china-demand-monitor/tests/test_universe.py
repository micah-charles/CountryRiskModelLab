import yaml
from pathlib import Path
from src.analysis.metrics_schema import Company
ROOT=Path(__file__).resolve().parents[1]
def test_seed_is_valid_and_unique():
    companies=[Company.model_validate(x) for x in yaml.safe_load((ROOT/"config/universe_seed.yaml").read_text())["companies"]]
    assert len(companies)>=26
    assert len({x.stock_code for x in companies})==len(companies)
    assert {"06862","02020","01211"}<={x.stock_code for x in companies}

