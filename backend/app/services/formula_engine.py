from __future__ import annotations

from math import sqrt
from statistics import NormalDist
from typing import Any, Callable

import numpy as np

from app.models.schemas import FormulaCalculationRequest, FormulaCalculationResponse, FormulaDefinition, FormulaStep, FormulaVariable, FormulaWorkedExample


def _variable(name: str, symbol: str, label: str, default: Any, unit: str, *, value_type: str = "number", minimum: float | None = None, maximum: float | None = None, step: float | None = None) -> FormulaVariable:
    return FormulaVariable(name=name, symbol=symbol, label=label, default=default, unit=unit, type=value_type, min=minimum, max=maximum, step=step)


def _definition(formula_id: str, name: str, family: str, question: str, latex: str, plain: str, method: str, variables: list[FormulaVariable], examples: list[FormulaWorkedExample], *, assumptions: list[str] | None = None, limitations: list[str] | None = None, related: list[str] | None = None, indicators: list[str] | None = None) -> FormulaDefinition:
    return FormulaDefinition(
        formula_id=formula_id,
        name=name,
        family=family,
        business_question=question,
        difficulty="intermediate" if family not in {"returns", "statistics"} else "foundational",
        latex=latex,
        plain_english=plain,
        variables=variables,
        assumptions=assumptions or [],
        limitations=limitations or [],
        calculation_method=method,
        worked_examples=examples,
        related_formula_ids=related or [],
        relevant_indicator_ids=indicators or [],
    )


_COMMON_LIMITATIONS = [
    "This is an educational approximation, not a production valuation model.",
    "Results depend on the input units and assumptions shown above.",
]


_FORMULAS: list[FormulaDefinition] = [
    _definition("RETURN_SIMPLE", "Simple return", "returns", "How much did a value change?", "r = (P_1 - P_0) / P_0", "The change relative to the starting value, expressed as a decimal.", "simple_return", [_variable("start_value", "P_0", "Start value", 100.0, "value"), _variable("end_value", "P_1", "End value", 105.0, "value")], [FormulaWorkedExample(name="5% increase", inputs={"start_value": 100, "end_value": 105}, expected_outputs={"return_decimal": 0.05})], limitations=["The start value must be non-zero."]),
    _definition("RETURN_PERCENTAGE", "Percentage return", "returns", "How can I show a return as a percentage?", "R\\% = 100 \\times r", "The simple return multiplied by 100 for display as a percentage.", "percentage_return", [_variable("start_value", "P_0", "Start value", 100.0, "value"), _variable("end_value", "P_1", "End value", 105.0, "value")], [FormulaWorkedExample(name="5 percent", inputs={"start_value": 100, "end_value": 105}, expected_outputs={"return_percent": 5.0})], limitations=["The start value must be non-zero."]),
    _definition("RATE_BASIS_POINT_CONVERSION", "Basis-point conversion", "rates", "How do I convert basis points into a decimal yield move?", "\\Delta y = bp / 10,000", "One basis point is one ten-thousandth in decimal yield terms.", "basis_point_conversion", [_variable("shock_bp", "bp", "Shock", 50.0, "bp", step=1)], [FormulaWorkedExample(name="50 basis points", inputs={"shock_bp": 50}, expected_outputs={"shock_decimal": 0.005})], assumptions=["The input is expressed in basis points."]),
    _definition("RATE_BOND_PRICE_SENSITIVITY", "Bond price sensitivity", "rates", "What is the approximate P&L when yields move?", "\\Delta P \\approx -D_{mod} \\times P \\times \\Delta y", "Bond prices generally fall when yields rise; modified duration scales the sensitivity.", "bond_price_sensitivity", [_variable("position_value", "P", "Position value", 100000000, "GBP", minimum=-1000000000, maximum=1000000000, step=1000000), _variable("modified_duration", "D_{mod}", "Modified duration", 18.0, "years", minimum=0, maximum=100, step=0.1), _variable("yield_shock_bp", "\\Delta y_{bp}", "Yield shock", 50.0, "bp", step=1)], [FormulaWorkedExample(name="Long gilt shock", inputs={"position_value": 100000000, "modified_duration": 18, "yield_shock_bp": 50}, expected_outputs={"estimated_pnl": -9000000})], assumptions=["Yield shock is converted from basis points to a decimal by dividing by 10,000."], limitations=_COMMON_LIMITATIONS + ["Large shocks, convexity, optionality, liquidity and basis risk are not captured.", "A signed position value uses positive for long and negative for short exposure."], related=["RATE_DV01", "RATE_CONVEXITY"], indicators=["GOVT_YIELD_30Y", "DV01"]),
    _definition("RATE_DURATION_MACAULAY", "Macaulay duration", "rates", "What is the weighted average timing of bond cash flows?", "D_{Mac} = \\frac{\\sum_t t \\times PV(CF_t)}{P}", "Macaulay duration is the present-value-weighted average time to receive the bond cash flows.", "macaulay_duration", [_variable("cash_flows", "CF_t", "Cash flows", [5, 5, 105], "currency", value_type="array"), _variable("periods", "t", "Periods", [1, 2, 3], "periods", value_type="array"), _variable("yield_rate", "y", "Yield per year", 0.05, "decimal", minimum=-0.99, maximum=10, step=0.001), _variable("frequency", "m", "Payments per year", 1, "per year", minimum=1, maximum=12, step=1)], [FormulaWorkedExample(name="Three cash flows", inputs={"cash_flows": [5, 5, 105], "periods": [1, 2, 3], "yield_rate": 0.05, "frequency": 1}, expected_outputs={"macaulay_duration": 2.86})], assumptions=["Cash-flow periods and yield compounding frequency are consistent."], limitations=["This assumes deterministic cash flows and a single yield curve point."]),
    _definition("RATE_DURATION_MODIFIED", "Modified duration", "rates", "How sensitive is a bond price to a small yield change?", "D_{mod} = \\frac{D_{Mac}}{1 + y/m}", "Modified duration converts Macaulay duration into a local price sensitivity.", "modified_duration", [_variable("macaulay_duration", "D_{Mac}", "Macaulay duration", 18.0, "years", minimum=0, maximum=100, step=0.1), _variable("yield_rate", "y", "Yield per year", 0.05, "decimal", minimum=-0.99, maximum=10, step=0.001), _variable("frequency", "m", "Payments per year", 1, "per year", minimum=1, maximum=12, step=1)], [FormulaWorkedExample(name="18-year duration", inputs={"macaulay_duration": 18, "yield_rate": 0.05, "frequency": 1}, expected_outputs={"modified_duration": 17.14})], assumptions=["The yield is represented as a decimal, not a percentage."]),
    _definition("RATE_DV01", "DV01 / PV01", "rates", "How much does a position change for one basis point?", "DV01 \\approx D_{mod} \\times P \\times 0.0001", "DV01 is the approximate signed P&L for a one basis-point rise in yield. The shock P&L is negative for a long position when yields rise.", "dv01", [_variable("position_value", "P", "Position value", 100000000, "GBP", minimum=-1000000000, maximum=1000000000, step=1000000), _variable("modified_duration", "D_{mod}", "Modified duration", 18.0, "years", minimum=0, maximum=100, step=0.1), _variable("yield_shock_bp", "\\Delta y_{bp}", "Yield shock", 50.0, "bp", step=1)], [FormulaWorkedExample(name="UK LDI teaching example", inputs={"position_value": 100000000, "modified_duration": 18, "yield_shock_bp": 50}, expected_outputs={"dv01_per_bp": 180000, "estimated_pnl": -9000000})], assumptions=["One basis point is 0.0001 in decimal yield terms."], limitations=_COMMON_LIMITATIONS + ["DV01 is local and linear; it does not capture convexity, margin or liquidity effects."], related=["RATE_BOND_PRICE_SENSITIVITY", "RATE_CONVEXITY"], indicators=["DV01", "GOVT_YIELD_30Y"]),
    _definition("RATE_CONVEXITY", "Convexity adjustment", "rates", "How can I improve a duration-only shock estimate?", "\\Delta P \\approx -D_{mod}P\\Delta y + \\frac{1}{2}CP(\\Delta y)^2", "Convexity adds the second-order curvature of the bond price-yield relationship.", "convexity_adjustment", [_variable("position_value", "P", "Position value", 100000000, "GBP", minimum=-1000000000, maximum=1000000000, step=1000000), _variable("modified_duration", "D_{mod}", "Modified duration", 18.0, "years", minimum=0, maximum=100, step=0.1), _variable("convexity", "C", "Convexity", 350.0, "years squared", minimum=0, maximum=10000, step=1), _variable("yield_shock_bp", "\\Delta y_{bp}", "Yield shock", 100.0, "bp", step=1)], [FormulaWorkedExample(name="100bp shock", inputs={"position_value": 100000000, "modified_duration": 18, "convexity": 350, "yield_shock_bp": 100}, expected_outputs={"convexity_adjusted_pnl": -16250000})], assumptions=["Convexity and duration are measured consistently for the position."], limitations=_COMMON_LIMITATIONS + ["This still omits optionality, liquidity, basis and changing risk sensitivities."], related=["RATE_DURATION_MODIFIED", "RATE_DV01"]),
    _definition("RATE_DURATION_PRICE", "Duration price sensitivity", "rates", "How does a yield shock translate into a bond price change?", "\\frac{\\Delta P}{P} \\approx -D_{mod} \\times \\Delta y", "A duration estimate expresses the approximate percentage price change from a small yield move.", "duration_price", [_variable("position_value", "P", "Position value", 100000000, "USD", minimum=-1000000000, maximum=1000000000, step=1000000), _variable("modified_duration", "D_{mod}", "Modified duration", 8.0, "years", minimum=0, maximum=100, step=0.1), _variable("yield_shock_bp", "\\Delta y_{bp}", "Yield shock", 20.0, "bp", step=1)], [FormulaWorkedExample(name="Treasury duration shock", inputs={"position_value": 100000000, "modified_duration": 8, "yield_shock_bp": 20}, expected_outputs={"price_return": -0.016, "estimated_pnl": -1600000})], assumptions=["Yield shock is converted from basis points to a decimal."], limitations=_COMMON_LIMITATIONS + ["This is a first-order approximation and omits convexity, liquidity, basis and optionality."], related=["RATE_BOND_PRICE_SENSITIVITY", "RATE_DV01"]),
    _definition("FX_DELTA", "FX position P&L", "fx", "What is the P&L from an FX-rate move?", "\\Delta P = N \\times \\delta_{FX} \\times \\Delta S", "FX P&L is the signed notional multiplied by the FX sensitivity and the change in the exchange rate.", "fx_delta", [_variable("position_notional", "N", "Position notional", 10000000, "quote currency", minimum=-1000000000, maximum=1000000000, step=100000), _variable("fx_delta", "\\delta_{FX}", "FX delta", 1.0, "sensitivity", step=0.01), _variable("fx_change", "\\Delta S", "FX-rate change", -0.04, "quote per base", step=0.0001)], [FormulaWorkedExample(name="Sterling weakens", inputs={"position_notional": 10000000, "fx_delta": 1, "fx_change": -0.04}, expected_outputs={"pnl": -400000})], assumptions=["The notional and FX change use compatible quote-currency units."], limitations=_COMMON_LIMITATIONS + ["This is a linear delta approximation and does not value forwards or options."]),
    _definition("FX_MOVE_PERCENT", "FX move percentage", "fx", "How large was an exchange-rate move?", "R_{FX} = S_1/S_0 - 1", "The percentage move in USD/JPY is the ending rate divided by the starting rate minus one; a negative result means USD/JPY fell and the yen strengthened.", "fx_move_percent", [_variable("entry_usdjpy", "S_0", "Entry USD/JPY", 160.03, "JPY per USD", minimum=0.000001, step=0.01), _variable("exit_usdjpy", "S_1", "Exit USD/JPY", 155.39, "JPY per USD", minimum=0.000001, step=0.01)], [FormulaWorkedExample(name="Two-day yen rally", inputs={"entry_usdjpy": 160.03, "exit_usdjpy": 155.39}, expected_outputs={"move_percent": -0.0289946})], assumptions=["Both observations use the same USD/JPY quotation convention."], limitations=["This describes the move; it does not explain causality or portfolio P&L."]),
    _definition("FX_UNHEDGED_CARRY_RETURN", "Unhedged FX carry return", "fx", "Can interest carry offset an adverse FX move?", "R = \\frac{(1+r_a h)S_1/S_0}{1+r_f h} - 1", "An unhedged carry return combines the asset carry, funding cost and exchange-rate move over the holding period.", "fx_unhedged_carry_return", [_variable("entry_usdjpy", "S_0", "Entry USD/JPY", 160.03, "JPY per USD", minimum=0.000001, step=0.01), _variable("exit_usdjpy", "S_1", "Exit USD/JPY", 155.39, "JPY per USD", minimum=0.000001, step=0.01), _variable("holding_days", "d", "Holding period", 2.0, "days", minimum=0, maximum=3650, step=1), _variable("usd_asset_yield_annual", "r_a", "USD asset yield", 0.05, "decimal", minimum=-1, maximum=10, step=0.001), _variable("jpy_funding_rate_annual", "r_f", "JPY funding rate", 0.01, "decimal", minimum=-1, maximum=10, step=0.001)], [FormulaWorkedExample(name="Two-day carry unwind", inputs={"entry_usdjpy": 160.03, "exit_usdjpy": 155.39, "holding_days": 2, "usd_asset_yield_annual": 0.05, "jpy_funding_rate_annual": 0.01}, expected_outputs={"unlevered_return": -0.0287818})], assumptions=["Rates are annual simple rates and the holding fraction is days divided by 365."], limitations=_COMMON_LIMITATIONS + ["This ignores transaction costs, margining, cross-currency basis, compounding, path dependence and liquidation mechanics."]),
    _definition("LEVERAGED_RETURN", "Simplified leveraged return", "fx", "How does leverage scale a learning return?", "R_{levered} = R_{unlevered} \\times L", "A simple teaching approximation multiplies an unlevered return by the stated leverage multiple.", "leveraged_return", [_variable("unlevered_return", "R", "Unlevered return", -0.0287818, "decimal", minimum=-100, maximum=100, step=0.001), _variable("leverage", "L", "Leverage", 3.0, "multiple", minimum=0, maximum=100, step=0.1)], [FormulaWorkedExample(name="Three-times carry position", inputs={"unlevered_return": -0.0287818, "leverage": 3}, expected_outputs={"leveraged_return": -0.0863453})], assumptions=["Leverage is represented as a simple multiplier."], limitations=["This does not model financing haircuts, margin calls, nonlinear liquidation, fees or path dependence."]),
    _definition("CURVE_2S10S", "2s10s yield-curve slope", "rates", "Is the 2-year to 10-year curve steepening or flattening?", "2s10s = y_{10Y} - y_{2Y}", "The 2s10s slope is the 10-year yield minus the 2-year yield, expressed in percentage points or basis points.", "curve_spread_bp", [_variable("yield_2y", "y_{2Y}", "2-year yield", 4.18, "%", step=0.01), _variable("yield_10y", "y_{10Y}", "10-year yield", 4.79, "%", step=0.01)], [FormulaWorkedExample(name="September 1 curve", inputs={"yield_2y": 4.18, "yield_10y": 4.79}, expected_outputs={"spread_pct": 0.61, "spread_bp": 61})], assumptions=["Both yields are quoted in percentage points with the same convention."], limitations=["A curve slope does not explain the separate drivers of each maturity."]),
    _definition("NOMINAL_REAL_INFLATION_PROXY", "Nominal-real yield gap", "rates", "What rough inflation-compensation proxy separates nominal and real yields?", "gap = y_{nominal,10Y} - y_{real,10Y}", "Subtracting a real yield from a nominal yield provides a rough market inflation-compensation proxy.", "nominal_real_gap", [_variable("nominal_10y_pct", "y_n", "Nominal 10-year yield", 4.96, "%", step=0.01), _variable("real_10y_pct", "y_r", "Real 10-year yield", 2.60, "%", step=0.01)], [FormulaWorkedExample(name="September 11 nominal-real gap", inputs={"nominal_10y_pct": 4.96, "real_10y_pct": 2.60}, expected_outputs={"gap_pct": 2.36})], assumptions=["The nominal and real yields are comparable maturities and quotation conventions."], limitations=["This is not a pure expected-inflation measure; it also contains inflation risk premia and technical differences."]),
    _definition("CREDIT_CS01", "Spread duration and CS01", "credit", "What is the P&L from a credit-spread move?", "CS01 = SD \\times P \\times 0.0001", "CS01 is the approximate signed P&L for a one basis-point increase in credit spread.", "credit_cs01", [_variable("position_value", "P", "Position value", 100000000, "currency", minimum=-1000000000, maximum=1000000000, step=1000000), _variable("spread_duration", "SD", "Spread duration", 5.0, "years", minimum=0, maximum=100, step=0.1), _variable("spread_shock_bp", "\\Delta s_{bp}", "Spread shock", 25.0, "bp", step=1)], [FormulaWorkedExample(name="25bp spread widening", inputs={"position_value": 100000000, "spread_duration": 5, "spread_shock_bp": 25}, expected_outputs={"cs01_per_bp": 50000, "estimated_pnl": -1250000})], assumptions=["A spread widening is adverse for a long credit position."], limitations=_COMMON_LIMITATIONS + ["Defaults, recovery, liquidity, curve shape and nonlinear instruments are not modelled."]),
    _definition("STAT_VARIANCE", "Variance", "statistics", "How dispersed are observations around their mean?", "s^2 = \\frac{\\sum_i(x_i-\\bar{x})^2}{n-1}", "Variance is the sample average squared distance from the mean.", "variance", [_variable("values", "x_i", "Observations", [1, 2, 3, 4, 5], "value", value_type="array")], [FormulaWorkedExample(name="Five observations", inputs={"values": [1, 2, 3, 4, 5]}, expected_outputs={"variance": 2.5})], limitations=["This uses sample variance with n-1 in the denominator."]),
    _definition("STAT_STANDARD_DEVIATION", "Standard deviation", "statistics", "What is the volatility implied by variance?", "s = \\sqrt{s^2}", "Standard deviation is variance expressed in the original unit.", "standard_deviation", [_variable("values", "x_i", "Observations", [1, 2, 3, 4, 5], "value", value_type="array")], [FormulaWorkedExample(name="Five observations", inputs={"values": [1, 2, 3, 4, 5]}, expected_outputs={"standard_deviation": 1.5811})], limitations=["Annualisation requires an appropriate frequency assumption."]),
    _definition("STAT_COVARIANCE", "Covariance", "statistics", "How do two variables move together?", "cov(x,y) = \\frac{\\sum_i(x_i-\\bar{x})(y_i-\\bar{y})}{n-1}", "Covariance is positive when two series tend to be above or below their means together.", "covariance", [_variable("x_values", "x_i", "X observations", [1, 2, 3, 4], "value", value_type="array"), _variable("y_values", "y_i", "Y observations", [2, 3, 5, 7], "value", value_type="array")], [FormulaWorkedExample(name="Two series", inputs={"x_values": [1, 2, 3, 4], "y_values": [2, 3, 5, 7]}, expected_outputs={"covariance": 2.1667})], limitations=["Covariance is scale-dependent and is not bounded."]),
    _definition("STAT_CORRELATION", "Correlation", "statistics", "How strong and directional is co-movement?", "\\rho_{xy} = \\frac{cov(x,y)}{s_xs_y}", "Correlation standardises covariance onto a -1 to +1 scale.", "correlation", [_variable("x_values", "x_i", "X observations", [1, 2, 3, 4], "value", value_type="array"), _variable("y_values", "y_i", "Y observations", [2, 3, 5, 7], "value", value_type="array")], [FormulaWorkedExample(name="Two series", inputs={"x_values": [1, 2, 3, 4], "y_values": [2, 3, 5, 7]}, expected_outputs={"correlation": 0.9898})], limitations=["Correlation does not prove causation and can change through a crisis."]),
    _definition("PORT_TWO_ASSET_VARIANCE", "Two-asset portfolio variance", "portfolio", "How does correlation change portfolio risk?", "\\sigma_p^2 = w_1^2\\sigma_1^2+w_2^2\\sigma_2^2+2w_1w_2\\sigma_1\\sigma_2\\rho_{12}", "Portfolio risk combines each asset's standalone risk and their co-movement.", "two_asset_portfolio_variance", [_variable("weight_1", "w_1", "Asset 1 weight", 0.6, "weight", minimum=-10, maximum=10, step=0.01), _variable("weight_2", "w_2", "Asset 2 weight", 0.4, "weight", minimum=-10, maximum=10, step=0.01), _variable("volatility_1", "\\sigma_1", "Asset 1 volatility", 0.1, "decimal", minimum=0, maximum=10, step=0.01), _variable("volatility_2", "\\sigma_2", "Asset 2 volatility", 0.2, "decimal", minimum=0, maximum=10, step=0.01), _variable("correlation", "\\rho_{12}", "Correlation", 0.2, "correlation", minimum=-1, maximum=1, step=0.01)], [FormulaWorkedExample(name="60/40 portfolio", inputs={"weight_1": 0.6, "weight_2": 0.4, "volatility_1": 0.1, "volatility_2": 0.2, "correlation": 0.2}, expected_outputs={"portfolio_volatility": 0.1092})], assumptions=["Volatilities are period-consistent decimals and correlation is between -1 and +1."], limitations=["This is a covariance-based approximation and depends on stable inputs."], related=["PORT_N_ASSET_VARIANCE", "STAT_CORRELATION"]),
    _definition("PORTFOLIO_VOLATILITY", "Portfolio volatility", "portfolio", "What is the volatility implied by a portfolio variance?", "\\sigma_p = \\sqrt{\\sigma_p^2}", "Portfolio volatility is the square root of portfolio variance, expressed in the same period and unit convention as the input.", "portfolio_volatility", [_variable("portfolio_variance", "\\sigma_p^2", "Portfolio variance", 0.01192464, "decimal squared", minimum=0, maximum=100, step=0.0001)], [FormulaWorkedExample(name="60/40 portfolio volatility", inputs={"portfolio_variance": 0.01192464}, expected_outputs={"portfolio_volatility": 0.1092})], assumptions=["The variance is non-negative and uses a known time period."], limitations=["Annualisation and comparability require consistent return frequency.", "Volatility is not a tail-loss measure and does not describe asymmetry or liquidity risk."], related=["PORT_TWO_ASSET_VARIANCE", "PORT_N_ASSET_VARIANCE", "STAT_STANDARD_DEVIATION"]),
    _definition("PORT_N_ASSET_VARIANCE", "N-asset portfolio variance", "portfolio", "How do all asset pairs contribute to risk?", "\\sigma_p^2 = \\mathbf{w}^T\\Sigma\\mathbf{w}", "The double summation adds every weighted asset-pair covariance contribution.", "n_asset_portfolio_variance", [_variable("weights", "w_i", "Weights", [0.6, 0.4], "weights", value_type="array"), _variable("volatilities", "\\sigma_i", "Volatilities", [0.1, 0.2], "decimal", value_type="array"), _variable("correlation_matrix", "\\rho_{ij}", "Correlation matrix", [[1, 0.2], [0.2, 1]], "correlation", value_type="matrix")], [FormulaWorkedExample(name="Two assets as a matrix", inputs={"weights": [0.6, 0.4], "volatilities": [0.1, 0.2], "correlation_matrix": [[1, 0.2], [0.2, 1]]}, expected_outputs={"portfolio_volatility": 0.1092})], assumptions=["The correlation matrix is square, symmetric and has ones on the diagonal."], limitations=["A covariance matrix is a model of co-movement, not a guarantee of future risk."]),
    _definition("VAR_PARAMETRIC", "Parametric Value at Risk", "var", "What loss threshold follows from volatility assumptions?", "VaR = z_c \\times \\sigma \\times |P| \\times \\sqrt{h}", "Parametric VaR scales position value and volatility by a confidence quantile and square-root time horizon.", "parametric_var", [_variable("position_value", "P", "Position value", 100000000, "currency", minimum=0, maximum=1000000000, step=1000000), _variable("volatility", "\\sigma", "Period volatility", 0.01, "decimal", minimum=0, maximum=10, step=0.001), _variable("confidence", "c", "Confidence", 0.99, "probability", minimum=0.5, maximum=0.9999, step=0.001), _variable("horizon_days", "h", "Horizon", 1, "days", minimum=1, maximum=1000, step=1)], [FormulaWorkedExample(name="99% one-day VaR", inputs={"position_value": 100000000, "volatility": 0.01, "confidence": 0.99, "horizon_days": 1}, expected_outputs={"var": 2326453.0})], assumptions=["Returns are approximately normal and volatility scales with the square root of time."], limitations=["Normality, liquidity, nonlinearity and tail dependence can make this underestimate stress losses."]),
    _definition("VAR_HISTORICAL", "Historical Value at Risk", "var", "What loss threshold is observed in a return history?", "VaR_c = quantile_c(-P r_i)", "Historical VaR takes an empirical quantile of losses generated by the supplied returns.", "historical_var", [_variable("returns", "r_i", "Historical returns", [-0.03, -0.01, 0.0, 0.01, 0.02], "decimal", value_type="array"), _variable("position_value", "P", "Position value", 100000000, "currency", minimum=0, maximum=1000000000, step=1000000), _variable("confidence", "c", "Confidence", 0.8, "probability", minimum=0.5, maximum=0.9999, step=0.01)], [FormulaWorkedExample(name="Empirical loss quantile", inputs={"returns": [-0.03, -0.01, 0, 0.01, 0.02], "position_value": 100000000, "confidence": 0.8}, expected_outputs={"var": 1000000})], assumptions=["The historical sample is representative of the risk horizon."]),
    _definition("ES_HISTORICAL", "Historical Expected Shortfall", "expected_shortfall", "How bad are losses beyond VaR on average?", "ES_c = E[L \\mid L \\ge VaR_c]", "Expected Shortfall averages the worst losses beyond the selected historical VaR threshold.", "historical_expected_shortfall", [_variable("returns", "r_i", "Historical returns", [-0.03, -0.01, 0.0, 0.01, 0.02], "decimal", value_type="array"), _variable("position_value", "P", "Position value", 100000000, "currency", minimum=0, maximum=1000000000, step=1000000), _variable("confidence", "c", "Confidence", 0.8, "probability", minimum=0.5, maximum=0.9999, step=0.01)], [FormulaWorkedExample(name="Empirical tail average", inputs={"returns": [-0.03, -0.01, 0, 0.01, 0.02], "position_value": 100000000, "confidence": 0.8}, expected_outputs={"expected_shortfall": 3000000})], assumptions=["The tail is estimated from the supplied historical observations."]),
    _definition("STRESS_SENSITIVITY", "Sensitivity stress P&L", "stress", "What is the result of applying a specified shock to a sensitivity?", "Stress P\\&L = sensitivity \\times shock", "A sensitivity stress applies a user-selected shock directly to a signed risk sensitivity.", "sensitivity_stress", [_variable("sensitivity_per_unit", "S", "Sensitivity per unit", -180000, "currency per bp", step=1000), _variable("shock_units", "\\Delta x", "Shock", 50, "bp", step=1)], [FormulaWorkedExample(name="Duration stress", inputs={"sensitivity_per_unit": -180000, "shock_units": 50}, expected_outputs={"stress_pnl": -9000000})], assumptions=["The sensitivity already carries the correct sign and unit."]),
]


def list_formula_definitions() -> list[FormulaDefinition]:
    return list(_FORMULAS)


def get_formula_definition(formula_id: str) -> FormulaDefinition:
    for definition in _FORMULAS:
        if definition.formula_id == formula_id:
            return definition
    raise ValueError(f"Formula not found: {formula_id}")


def _number(parameters: dict[str, Any], key: str) -> float:
    value = parameters.get(key)
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Formula input '{key}' must be numeric.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Formula input '{key}' must be numeric.") from exc
    if not np.isfinite(result):
        raise ValueError(f"Formula input '{key}' must be finite.")
    return result


def _array(parameters: dict[str, Any], key: str) -> list[float]:
    value = parameters.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Formula input '{key}' must be a non-empty array.")
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Formula input '{key}' must contain numbers.") from exc
    if not all(np.isfinite(result)):
        raise ValueError(f"Formula input '{key}' must contain finite numbers.")
    return result


def _matrix(parameters: dict[str, Any], key: str) -> list[list[float]]:
    value = parameters.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(row, list) for row in value):
        raise ValueError(f"Formula input '{key}' must be a non-empty matrix.")
    try:
        result = [[float(item) for item in row] for row in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Formula input '{key}' must contain numbers.") from exc
    size = len(result)
    if any(len(row) != size for row in result) or any(not np.isfinite(item) for row in result for item in row):
        raise ValueError(f"Formula input '{key}' must be a finite square matrix.")
    return result


def _same_length(left: list[float], right: list[float]) -> None:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Formula arrays must have the same length and at least two observations.")


def _confidence(value: float) -> None:
    if not 0.5 <= value < 1:
        raise ValueError("Confidence must be at least 0.5 and below 1.")


def _money(value: float) -> float:
    return round(float(value), 6)


def _calculate(formula_id: str, p: dict[str, Any]) -> tuple[dict[str, Any], str, list[FormulaStep]]:
    if formula_id in {"RETURN_SIMPLE", "RETURN_PERCENTAGE"}:
        start, end = _number(p, "start_value"), _number(p, "end_value")
        if start == 0:
            raise ValueError("Start value must not be zero.")
        result = (end - start) / start
        outputs = {"return_decimal": result, "return_percent": result * 100}
        steps = [FormulaStep(label="Change", expression=f"{end:g} - {start:g}", result=end - start), FormulaStep(label="Simple return", expression=f"({end:g} - {start:g}) / {start:g}", result=result), FormulaStep(label="Percentage return", expression=f"{result:g} x 100", result=result * 100)]
        return outputs, f"The value changed by {result * 100:.2f}%.", steps

    if formula_id == "RATE_BASIS_POINT_CONVERSION":
        shock_bp = _number(p, "shock_bp")
        shock_decimal = shock_bp / 10000
        steps = [FormulaStep(label="Decimal yield move", expression=f"{shock_bp:g} / 10,000", result=shock_decimal)]
        return {"shock_decimal": _money(shock_decimal)}, f"{shock_bp:g}bp equals a {shock_decimal:.6f} decimal yield move.", steps

    if formula_id in {"RATE_BOND_PRICE_SENSITIVITY", "RATE_DURATION_PRICE", "RATE_DV01"}:
        position, duration, shock_bp = _number(p, "position_value"), _number(p, "modified_duration"), _number(p, "yield_shock_bp")
        dv01 = duration * position * 0.0001
        pnl = -dv01 * shock_bp
        outputs = {"dv01_per_bp": _money(dv01), "estimated_pnl": _money(pnl), "yield_shock_decimal": shock_bp / 10000}
        steps = [FormulaStep(label="Basis-point conversion", expression=f"{shock_bp:g} / 10,000", result=shock_bp / 10000), FormulaStep(label="DV01", expression=f"{duration:g} x {position:g} x 0.0001", result=_money(dv01)), FormulaStep(label="Apply shock", expression=f"-{dv01:g} x {shock_bp:g}", result=_money(pnl))]
        if formula_id == "RATE_DURATION_PRICE":
            outputs["price_return"] = _money(pnl / position) if position else 0
        return outputs, f"A {shock_bp:g}bp yield move produces an estimated {pnl:,.0f} loss/P&L under the duration approximation.", steps

    if formula_id == "RATE_DURATION_MACAULAY":
        cash_flows, periods = _array(p, "cash_flows"), _array(p, "periods")
        _same_length(cash_flows, periods)
        yield_rate, frequency = _number(p, "yield_rate"), _number(p, "frequency")
        if frequency <= 0 or 1 + yield_rate / frequency <= 0:
            raise ValueError("Yield and frequency must produce a positive discount factor.")
        discount = 1 + yield_rate / frequency
        pv = [cash / discount**period for cash, period in zip(cash_flows, periods)]
        price = sum(pv)
        duration = sum(period * cash for period, cash in zip(periods, pv)) / price / frequency
        steps = [FormulaStep(label="Present value", expression="sum(CF_t / (1 + y/m)^t)", result=_money(price)), FormulaStep(label="Macaulay duration", expression="sum(t x PV(CF_t)) / price / m", result=_money(duration))]
        return {"price": _money(price), "macaulay_duration": _money(duration)}, f"The cash-flow weighted duration is {duration:.2f} years.", steps

    if formula_id == "RATE_DURATION_MODIFIED":
        macaulay, yield_rate, frequency = _number(p, "macaulay_duration"), _number(p, "yield_rate"), _number(p, "frequency")
        if frequency <= 0 or 1 + yield_rate / frequency <= 0:
            raise ValueError("Yield and frequency must produce a positive denominator.")
        modified = macaulay / (1 + yield_rate / frequency)
        steps = [FormulaStep(label="Modified duration", expression=f"{macaulay:g} / (1 + {yield_rate:g} / {frequency:g})", result=_money(modified))]
        return {"modified_duration": _money(modified)}, f"Modified duration is {modified:.2f} years.", steps

    if formula_id == "RATE_CONVEXITY":
        position, duration, convexity, shock_bp = _number(p, "position_value"), _number(p, "modified_duration"), _number(p, "convexity"), _number(p, "yield_shock_bp")
        shock = shock_bp / 10000
        duration_pnl = -duration * position * shock
        convexity_pnl = 0.5 * convexity * position * shock**2
        total = duration_pnl + convexity_pnl
        steps = [FormulaStep(label="Duration term", expression=f"-{duration:g} x {position:g} x {shock:g}", result=_money(duration_pnl)), FormulaStep(label="Convexity term", expression=f"0.5 x {convexity:g} x {position:g} x {shock:g}^2", result=_money(convexity_pnl)), FormulaStep(label="Total approximation", expression=f"{duration_pnl:g} + {convexity_pnl:g}", result=_money(total))]
        return {"duration_pnl": _money(duration_pnl), "convexity_pnl": _money(convexity_pnl), "convexity_adjusted_pnl": _money(total)}, f"The duration plus convexity estimate is {total:,.0f}.", steps

    if formula_id == "FX_MOVE_PERCENT":
        entry, exit = _number(p, "entry_usdjpy"), _number(p, "exit_usdjpy")
        if entry == 0:
            raise ValueError("Entry USD/JPY must not be zero.")
        move = exit / entry - 1
        steps = [FormulaStep(label="FX move", expression=f"{exit:g} / {entry:g} - 1", result=_money(move))]
        return {"move_decimal": _money(move), "move_percent": _money(move * 100)}, f"USD/JPY moved {move:.2%}; a negative move means the yen strengthened.", steps

    if formula_id == "FX_UNHEDGED_CARRY_RETURN":
        entry, exit = _number(p, "entry_usdjpy"), _number(p, "exit_usdjpy")
        holding_days = _number(p, "holding_days")
        asset_rate = _number(p, "usd_asset_yield_annual")
        funding_rate = _number(p, "jpy_funding_rate_annual")
        if entry == 0 or holding_days < 0:
            raise ValueError("Entry USD/JPY must not be zero and holding days must be non-negative.")
        holding_fraction = holding_days / 365
        asset_growth = 1 + asset_rate * holding_fraction
        funding_growth = 1 + funding_rate * holding_fraction
        if asset_growth <= 0 or funding_growth <= 0:
            raise ValueError("Rates and holding period must produce positive growth factors.")
        spot_component = exit / entry - 1
        unlevered = (asset_growth * exit / entry) / funding_growth - 1
        steps = [FormulaStep(label="Holding fraction", expression=f"{holding_days:g} / 365", result=_money(holding_fraction)), FormulaStep(label="Spot return", expression=f"{exit:g} / {entry:g} - 1", result=_money(spot_component)), FormulaStep(label="Carry-adjusted return", expression=f"((1 + {asset_rate:g} x h) x {exit:g}/{entry:g}) / (1 + {funding_rate:g} x h) - 1", result=_money(unlevered))]
        return {"holding_fraction": _money(holding_fraction), "spot_return_component": _money(spot_component), "unlevered_return": _money(unlevered)}, f"The estimated unlevered carry return is {unlevered:.2%}.", steps

    if formula_id == "LEVERAGED_RETURN":
        unlevered, leverage = _number(p, "unlevered_return"), _number(p, "leverage")
        if leverage < 0:
            raise ValueError("Leverage must be non-negative.")
        result = unlevered * leverage
        steps = [FormulaStep(label="Leveraged return", expression=f"{unlevered:g} x {leverage:g}", result=_money(result))]
        return {"leveraged_return": _money(result)}, f"The simplified leveraged return is {result:.2%}.", steps

    if formula_id == "CURVE_2S10S":
        yield_2y, yield_10y = _number(p, "yield_2y"), _number(p, "yield_10y")
        spread_pct = yield_10y - yield_2y
        steps = [FormulaStep(label="2s10s slope", expression=f"{yield_10y:g} - {yield_2y:g}", result=_money(spread_pct))]
        return {"spread_pct": _money(spread_pct), "spread_bp": _money(spread_pct * 100)}, f"The 2s10s slope is {spread_pct:.2f} percentage points ({spread_pct * 100:.0f}bp).", steps

    if formula_id == "NOMINAL_REAL_INFLATION_PROXY":
        nominal, real = _number(p, "nominal_10y_pct"), _number(p, "real_10y_pct")
        gap = nominal - real
        steps = [FormulaStep(label="Nominal-real gap", expression=f"{nominal:g} - {real:g}", result=_money(gap))]
        return {"gap_pct": _money(gap)}, f"The rough nominal-real gap is {gap:.2f} percentage points.", steps

    if formula_id == "FX_DELTA":
        notional, delta, change = _number(p, "position_notional"), _number(p, "fx_delta"), _number(p, "fx_change")
        pnl = notional * delta * change
        steps = [FormulaStep(label="FX P&L", expression=f"{notional:g} x {delta:g} x {change:g}", result=_money(pnl))]
        return {"pnl": _money(pnl)}, f"The estimated FX P&L is {pnl:,.0f}.", steps

    if formula_id == "CREDIT_CS01":
        position, duration, shock = _number(p, "position_value"), _number(p, "spread_duration"), _number(p, "spread_shock_bp")
        cs01 = duration * position * 0.0001
        pnl = -cs01 * shock
        steps = [FormulaStep(label="CS01", expression=f"{duration:g} x {position:g} x 0.0001", result=_money(cs01)), FormulaStep(label="Apply spread shock", expression=f"-{cs01:g} x {shock:g}", result=_money(pnl))]
        return {"cs01_per_bp": _money(cs01), "estimated_pnl": _money(pnl)}, f"The estimated credit-spread P&L is {pnl:,.0f}.", steps

    if formula_id in {"STAT_VARIANCE", "STAT_STANDARD_DEVIATION"}:
        values = np.asarray(_array(p, "values"), dtype=float)
        if len(values) < 2:
            raise ValueError("Sample variance requires at least two observations.")
        variance = float(np.var(values, ddof=1))
        standard_deviation = sqrt(variance)
        steps = [FormulaStep(label="Mean", expression="sum(values) / n", result=_money(float(values.mean()))), FormulaStep(label="Sample variance", expression="sum((x - mean)^2) / (n - 1)", result=_money(variance)), FormulaStep(label="Standard deviation", expression="sqrt(variance)", result=_money(standard_deviation))]
        return {"variance": _money(variance), "standard_deviation": _money(standard_deviation)}, f"The sample standard deviation is {standard_deviation:.4f}.", steps

    if formula_id in {"STAT_COVARIANCE", "STAT_CORRELATION"}:
        x, y = _array(p, "x_values"), _array(p, "y_values")
        _same_length(x, y)
        covariance = float(np.cov(x, y, ddof=1)[0, 1])
        correlation = float(np.corrcoef(x, y)[0, 1])
        if not np.isfinite(correlation):
            raise ValueError("Correlation is undefined when one series has zero variance.")
        steps = [FormulaStep(label="Covariance", expression="sum((x - mean_x)(y - mean_y)) / (n - 1)", result=_money(covariance)), FormulaStep(label="Correlation", expression="covariance / (std_x x std_y)", result=_money(correlation))]
        return {"covariance": _money(covariance), "correlation": _money(correlation)}, f"The correlation is {correlation:.4f}.", steps

    if formula_id == "PORT_TWO_ASSET_VARIANCE":
        w1, w2, v1, v2, corr = (_number(p, key) for key in ("weight_1", "weight_2", "volatility_1", "volatility_2", "correlation"))
        if not -1 <= corr <= 1:
            raise ValueError("Correlation must be between -1 and +1.")
        variance = w1**2 * v1**2 + w2**2 * v2**2 + 2 * w1 * w2 * v1 * v2 * corr
        if variance < -1e-12:
            raise ValueError("The supplied inputs produce a negative portfolio variance.")
        variance = max(variance, 0)
        standalone = sqrt(w1**2 * v1**2 + w2**2 * v2**2)
        volatility = sqrt(variance)
        steps = [FormulaStep(label="Pair covariance term", expression=f"2 x {w1:g} x {w2:g} x {v1:g} x {v2:g} x {corr:g}", result=_money(2 * w1 * w2 * v1 * v2 * corr)), FormulaStep(label="Portfolio variance", expression="w1^2v1^2 + w2^2v2^2 + pair term", result=_money(variance)), FormulaStep(label="Portfolio volatility", expression="sqrt(portfolio variance)", result=_money(volatility))]
        return {"portfolio_variance": _money(variance), "portfolio_volatility": _money(volatility), "standalone_volatility": _money(standalone), "diversification_benefit": _money(standalone - volatility)}, f"Portfolio volatility is {volatility:.2%}; diversification benefit is {standalone - volatility:.2%} versus standalone risk.", steps

    if formula_id == "PORT_N_ASSET_VARIANCE":
        weights, volatilities, correlations = _array(p, "weights"), _array(p, "volatilities"), _matrix(p, "correlation_matrix")
        if len(weights) != len(volatilities) or len(weights) != len(correlations):
            raise ValueError("Weights, volatilities, and correlation matrix dimensions must match.")
        if any(abs(correlation) > 1 for row in correlations for correlation in row):
            raise ValueError("Correlation entries must be between -1 and +1.")
        if any(abs(correlations[i][j] - correlations[j][i]) > 1e-9 for i in range(len(correlations)) for j in range(len(correlations))):
            raise ValueError("Correlation matrix must be symmetric.")
        covariance = np.diag(volatilities) @ np.asarray(correlations) @ np.diag(volatilities)
        variance = float(np.asarray(weights) @ covariance @ np.asarray(weights))
        if variance < -1e-12:
            raise ValueError("The supplied matrix produces a negative portfolio variance.")
        volatility = sqrt(max(variance, 0))
        steps = [FormulaStep(label="Covariance matrix", expression="diag(volatility) x correlation x diag(volatility)", result=covariance.round(10).tolist()), FormulaStep(label="Portfolio variance", expression="w^T x covariance x w", result=_money(variance)), FormulaStep(label="Portfolio volatility", expression="sqrt(portfolio variance)", result=_money(volatility))]
        return {"portfolio_variance": _money(variance), "portfolio_volatility": _money(volatility)}, f"Portfolio volatility is {volatility:.2%} across {len(weights)} assets.", steps

    if formula_id == "PORTFOLIO_VOLATILITY":
        variance = _number(p, "portfolio_variance")
        if variance < 0:
            raise ValueError("Portfolio variance must be non-negative.")
        volatility = sqrt(variance)
        steps = [FormulaStep(label="Portfolio volatility", expression=f"sqrt({variance:g})", result=_money(volatility))]
        return {"portfolio_volatility": _money(volatility)}, f"Portfolio volatility is {volatility:.2%} for the supplied period.", steps

    if formula_id == "VAR_PARAMETRIC":
        position, volatility, confidence, horizon = _number(p, "position_value"), _number(p, "volatility"), _number(p, "confidence"), _number(p, "horizon_days")
        _confidence(confidence)
        if volatility < 0 or horizon <= 0:
            raise ValueError("Volatility must be non-negative and horizon must be positive.")
        z = NormalDist().inv_cdf(confidence)
        var = abs(position) * volatility * z * sqrt(horizon)
        steps = [FormulaStep(label="Confidence quantile", expression=f"z({confidence:g})", result=_money(z)), FormulaStep(label="Horizon scaling", expression=f"sqrt({horizon:g})", result=_money(sqrt(horizon))), FormulaStep(label="Parametric VaR", expression=f"{z:g} x {volatility:g} x |{position:g}| x sqrt({horizon:g})", result=_money(var))]
        return {"var": _money(var), "z_score": _money(z)}, f"The estimated {confidence:.2%} VaR is {var:,.0f}.", steps

    if formula_id in {"VAR_HISTORICAL", "ES_HISTORICAL"}:
        returns, position, confidence = _array(p, "returns"), _number(p, "position_value"), _number(p, "confidence")
        _confidence(confidence)
        if len(returns) < 3 or position < 0:
            raise ValueError("Historical risk needs at least three observations and a non-negative position value.")
        losses = np.sort(-position * np.asarray(returns))
        var = float(np.quantile(losses, confidence, method="linear"))
        tail = losses[losses >= var - 1e-9]
        expected_shortfall = float(tail.mean()) if len(tail) else var
        steps = [FormulaStep(label="Loss observations", expression="-position x returns", result=losses.round(6).tolist()), FormulaStep(label="Historical VaR", expression=f"quantile(losses, {confidence:g})", result=_money(var)), FormulaStep(label="Expected Shortfall", expression="mean(losses >= VaR)", result=_money(expected_shortfall))]
        outputs = {"var": _money(var), "expected_shortfall": _money(expected_shortfall)}
        headline = f"Historical VaR is {var:,.0f}; the average loss beyond it is {expected_shortfall:,.0f}."
        return outputs, headline, steps

    if formula_id == "STRESS_SENSITIVITY":
        sensitivity, shock = _number(p, "sensitivity_per_unit"), _number(p, "shock_units")
        pnl = sensitivity * shock
        steps = [FormulaStep(label="Sensitivity stress", expression=f"{sensitivity:g} x {shock:g}", result=_money(pnl))]
        return {"stress_pnl": _money(pnl)}, f"The sensitivity stress P&L is {pnl:,.0f}.", steps

    raise ValueError(f"Formula implementation not found: {formula_id}")


def calculate_formula(request: FormulaCalculationRequest) -> FormulaCalculationResponse:
    definition = get_formula_definition(request.formula_id)
    outputs, headline, steps = _calculate(request.formula_id, request.parameters)
    return FormulaCalculationResponse(
        formula_id=request.formula_id,
        input_origin=request.input_origin,
        parameters=request.parameters,
        outputs=outputs,
        headline=headline,
        steps=steps,
        assumptions=definition.assumptions,
        limitations=definition.limitations,
    )
