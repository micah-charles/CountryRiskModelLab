from src.hkex.metadata import is_annual_report,canonical_url,normalize_title
def test_annual_report_title_filter():
    assert is_annual_report("Financial Statements/ESG Information - [Annual Report] Annual Report 2024")
    assert is_annual_report("2024 年度報告")
    assert not is_annual_report("Environmental, Social and Governance Report 2024")
def test_normalization():
    assert normalize_title("Annual Report 2024") == "annual-report-2024"
    assert canonical_url("HTTPS://WWW.HKEXNEWS.HK//a.pdf#p=2")=="https://www.hkexnews.hk/a.pdf"

