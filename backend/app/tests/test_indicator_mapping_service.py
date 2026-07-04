from app.services.indicator_mapping_service import load_indicator_mapping


def test_supported_imf_indicators_load_from_json_mapping():
    mapping = load_indicator_mapping()
    assert "NGDP_RPCH" in mapping
    assert mapping["PCPIPCH"].platform_variable == "inflation_yoy"
    assert mapping["GGXWDG_NGDP"].expected_relationship_to_bond_yield == "positive"

