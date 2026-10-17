from src.analysis.scorer import score_row
def test_scores_bounded_and_missing_reweighted():
    weights={"revenue_china_yoy":.5,"same_store_sales_growth":.5}
    score,confidence,parts=score_row({"revenue_yoy":"-12","same_store_sales_growth":"-4"},None,weights)
    assert score==4.5 and confidence==1 and 0<=score<=5
def test_single_component_is_not_enough_to_score():
    score,confidence,_=score_row({"revenue_yoy":"-12"},None,{"revenue_china_yoy":.5,"same_store_sales_growth":.5})
    assert score is None and confidence==.5
def test_no_supported_inputs_is_missing():
    score,confidence,_=score_row({},None,{"revenue_china_yoy":1})
    assert score is None and confidence==0
