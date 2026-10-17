from src.analysis.financial_extractors import find_metric,parse_number
def test_metric_with_exact_evidence_span():
    text="Management Discussion\nGross profit margin increased to 62.5% in 2024.\n"
    result=find_metric(text,["gross profit margin"],"percentage","")
    assert result and result[0]==62.5 and "62.5%" in result[4]
def test_units():
    assert parse_number("(1,200) million")==-1_200_000_000
