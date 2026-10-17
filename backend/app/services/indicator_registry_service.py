from __future__ import annotations

from app.models.schemas import IndicatorDefinition


_INDICATORS = [
    IndicatorDefinition(indicator_id="POLICY_RATE", name="Policy rate", family="rates", description="Central-bank policy rate.", unit="percent", direction_semantics="higher is tighter", frequency="monthly", source="central_bank", display_format="0.00%"),
    IndicatorDefinition(indicator_id="GOVT_YIELD_2Y", name="2-year government yield", family="rates", description="Short government benchmark yield.", unit="percent", direction_semantics="higher means higher discount rate", frequency="daily", source="market_data", display_format="0.00%"),
    IndicatorDefinition(indicator_id="GOVT_YIELD_5Y", name="5-year government yield", family="rates", description="Intermediate government benchmark yield.", unit="percent", direction_semantics="higher means higher discount rate", frequency="daily", source="market_data", display_format="0.00%"),
    IndicatorDefinition(indicator_id="GOVT_YIELD_10Y", name="10-year government yield", family="rates", description="Common sovereign benchmark yield.", unit="percent", direction_semantics="higher means higher discount rate", frequency="daily", source="market_data", display_format="0.00%"),
    IndicatorDefinition(indicator_id="GOVT_YIELD_30Y", name="30-year government yield", family="rates", description="Long government benchmark yield.", unit="percent", direction_semantics="higher means higher discount rate", frequency="daily", source="market_data", display_format="0.00%"),
    IndicatorDefinition(indicator_id="UK_GILT_30Y_MOVE", name="30-year gilt yield move", family="rates", description="Verified event-day move in the UK long gilt yield.", unit="bp", direction_semantics="up means yield increased", frequency="event", source="UK Parliament inquiry", display_format="+0.0 bp"),
    IndicatorDefinition(indicator_id="CURVE_2S10S", name="2s10s curve slope", family="rates", description="10-year yield minus 2-year yield.", unit="basis points", direction_semantics="higher means steeper curve", frequency="daily", source="market_data", transformation="y10 - y2", display_format="+0 bp"),
    IndicatorDefinition(indicator_id="GBPUSD", name="GBP/USD", family="fx", description="US dollars per pound sterling.", unit="USD per GBP", direction_semantics="higher means GBP appreciation", frequency="daily", source="Bank of England Database", source_series_id="XUDLUSS", display_format="0.0000"),
    IndicatorDefinition(indicator_id="FX_SPOT", name="FX spot rate", family="fx", description="Spot exchange rate for a selected currency pair.", unit="quote per base", direction_semantics="pair-specific", frequency="daily", source="market_data", display_format="0.0000"),
    IndicatorDefinition(indicator_id="FTSE100", name="FTSE 100", family="equity", description="Broad UK equity index.", unit="index points", direction_semantics="higher means equity appreciation", frequency="daily", source="market_data", display_format="0.0"),
    IndicatorDefinition(indicator_id="EQUITY_VOL", name="Equity volatility", family="volatility", description="Implied or realized volatility for an equity market.", unit="percent", direction_semantics="higher means more uncertainty", frequency="daily", source="market_data", display_format="0.0%"),
    IndicatorDefinition(indicator_id="FX_VOL", name="FX volatility", family="volatility", description="Implied or realized volatility for an FX pair.", unit="percent", direction_semantics="higher means more uncertainty", frequency="daily", source="market_data", display_format="0.0%"),
    IndicatorDefinition(indicator_id="IG_SPREAD", name="Investment-grade spread", family="credit", description="Investment-grade credit spread over a reference curve.", unit="bp", direction_semantics="higher means wider credit risk premium", frequency="daily", source="market_data", display_format="0 bp"),
    IndicatorDefinition(indicator_id="HY_SPREAD", name="High-yield spread", family="credit", description="High-yield credit spread over a reference curve.", unit="bp", direction_semantics="higher means wider credit risk premium", frequency="daily", source="market_data", display_format="0 bp"),
    IndicatorDefinition(indicator_id="CPI", name="Consumer price inflation", family="macro", description="Consumer price inflation rate.", unit="percent", direction_semantics="higher means more inflation pressure", frequency="monthly", source="statistical_agency", display_format="0.0%"),
    IndicatorDefinition(indicator_id="GDP_GROWTH", name="GDP growth", family="macro", description="Real GDP growth rate.", unit="percent", direction_semantics="higher means stronger growth", frequency="quarterly", source="statistical_agency", display_format="0.0%"),
    IndicatorDefinition(indicator_id="UNEMPLOYMENT", name="Unemployment rate", family="macro", description="Share of the labour force unemployed.", unit="percent", direction_semantics="higher means weaker labour market", frequency="monthly", source="statistical_agency", display_format="0.0%"),
    IndicatorDefinition(indicator_id="FISCAL_BALANCE", name="Fiscal balance", family="macro", description="General-government fiscal balance.", unit="percent of GDP", direction_semantics="higher means stronger balance", frequency="annual", source="official", display_format="0.0% GDP"),
    IndicatorDefinition(indicator_id="LDI_LIQUIDITY_STRESS", name="LDI liquidity stress", family="market_risk", description="Case indicator for the documented LDI liquidity mechanism; it is not a generic market price series.", unit="qualitative", direction_semantics="higher means more stress", frequency="event", source="UK Parliament inquiry", display_format="text"),
    IndicatorDefinition(indicator_id="BOE_TEMP_GILT_PURCHASES", name="BoE temporary gilt purchases", family="policy", description="Temporary financial-stability gilt purchases reported for the case.", unit="GBP bn", direction_semantics="higher means greater intervention size", frequency="event", source="Bank of England", display_format="0.0 GBP bn"),
    IndicatorDefinition(indicator_id="DV01", name="DV01/PV01", family="market_risk", description="Approximate signed price change for a one basis-point yield move.", unit="currency per bp", direction_semantics="signed by position direction", frequency="calculated", source="formula_engine", display_format="currency"),
    IndicatorDefinition(indicator_id="CS01", name="CS01", family="market_risk", description="Approximate spread P&L for a one basis-point credit-spread move.", unit="currency per bp", direction_semantics="signed by position direction", frequency="calculated", source="formula_engine", display_format="currency"),
    IndicatorDefinition(indicator_id="FX_DELTA", name="FX delta", family="market_risk", description="P&L sensitivity to a change in an FX rate.", unit="currency per rate unit", direction_semantics="signed exposure", frequency="calculated", source="formula_engine", display_format="currency"),
    IndicatorDefinition(indicator_id="VAR_99", name="99% Value at Risk", family="market_risk", description="Loss threshold not expected to be exceeded at the selected confidence level under the model assumptions.", unit="currency", direction_semantics="higher means more loss risk", frequency="calculated", source="formula_engine", display_format="currency"),
    IndicatorDefinition(indicator_id="EXPECTED_SHORTFALL", name="Expected Shortfall", family="market_risk", description="Average loss in the tail beyond the selected VaR threshold.", unit="currency", direction_semantics="higher means more tail risk", frequency="calculated", source="formula_engine", display_format="currency"),
    IndicatorDefinition(indicator_id="STRESS_LOSS", name="Stress loss", family="market_risk", description="Loss under a specified sensitivity or scenario shock.", unit="currency", direction_semantics="higher means more loss", frequency="calculated", source="formula_engine", display_format="currency"),
]


def list_indicator_definitions() -> list[IndicatorDefinition]:
    return list(_INDICATORS)


def get_indicator_definition(indicator_id: str) -> IndicatorDefinition:
    for definition in _INDICATORS:
        if definition.indicator_id == indicator_id:
            return definition
    raise ValueError(f"Indicator not found: {indicator_id}")

