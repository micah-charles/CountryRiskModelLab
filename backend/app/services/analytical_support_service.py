from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas import AnalyticalSupport, AnalyticalSupportType
from app.services.formula_engine import get_formula_definition


class TransmissionChannel(BaseModel):
    label: str
    description: str
    direction: str = "conditional"


class TransmissionDefinition(BaseModel):
    transmission_id: str
    title: str
    summary: str
    trigger: str
    channels: list[TransmissionChannel] = Field(default_factory=list)
    countervailing_channels: list[TransmissionChannel] = Field(default_factory=list)
    expected_relationship: str
    limitations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class AnalyticalSupportDefinition(BaseModel):
    support_type: AnalyticalSupportType
    reference_id: str | None = None
    title: str
    summary: str
    available_before_reveal: bool = True
    formula: dict[str, Any] | None = None
    transmission: TransmissionDefinition | None = None
    model: dict[str, Any] | None = None
    identity: dict[str, Any] | None = None
    rule_of_thumb: dict[str, Any] | None = None


_TRANSMISSIONS: dict[str, TransmissionDefinition] = {
    "FISCAL_TO_LONG_YIELDS": TransmissionDefinition(
        transmission_id="FISCAL_TO_LONG_YIELDS",
        title="Fiscal loosening and long-term yields",
        summary="Fiscal announcements can change expected borrowing, inflation expectations and the term or fiscal risk premium.",
        trigger="Large or unfunded fiscal easing is announced while inflation is already elevated.",
        channels=[
            TransmissionChannel(label="Expected borrowing", description="Higher expected government borrowing can increase the supply of duration that investors need to absorb.", direction="upward pressure on yields"),
            TransmissionChannel(label="Inflation expectations", description="A fiscal impulse may change the expected path of inflation and policy rates.", direction="upward pressure on yields"),
            TransmissionChannel(label="Fiscal and term premium", description="A credibility shock can increase compensation demanded for holding long maturity government debt.", direction="upward pressure on yields"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="Growth expectations", description="A growth shock or expected policy reversal can pull yields lower.", direction="downward pressure on yields"),
            TransmissionChannel(label="Safe-haven demand", description="A broader risk-off move can increase demand for high-quality government bonds.", direction="downward pressure on yields"),
            TransmissionChannel(label="Central-bank intervention", description="Official purchases or communication can interrupt the repricing.", direction="conditional"),
        ],
        expected_relationship="Long-dated yields tend to face upward pressure, but this framework supports a directional hypothesis and does not mechanically determine the size or timing of the move.",
        limitations=["The net effect depends on monetary policy, growth, global risk appetite, positioning and market liquidity.", "This is an economic transmission mechanism, not a deterministic forecasting equation."],
    ),
    "FISCAL_CONFIDENCE_TO_FX": TransmissionDefinition(
        transmission_id="FISCAL_CONFIDENCE_TO_FX",
        title="Fiscal confidence shock and sterling",
        summary="A loss of fiscal credibility can reduce demand for domestic assets, while higher expected policy rates can provide an offsetting FX channel.",
        trigger="A fiscal package sharply undermines investor confidence in the policy framework.",
        channels=[
            TransmissionChannel(label="Risk premium", description="Fiscal credibility falls and the risk premium on domestic assets rises.", direction="downward pressure on GBP"),
            TransmissionChannel(label="Asset demand", description="Lower demand for domestic assets can reduce demand for sterling.", direction="downward pressure on GBP"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="Expected Bank Rate", description="Expected policy tightening can widen the interest-rate differential and support sterling.", direction="upward pressure on GBP"),
            TransmissionChannel(label="Risk-off flows", description="Global safe-haven flows can dominate the domestic fiscal channel.", direction="conditional"),
        ],
        expected_relationship="Sterling may weaken when the confidence channel dominates; the direction and magnitude are conditional because FX is driven by competing cross-asset forces.",
        limitations=["Short-horizon FX moves can deviate substantially from interest-rate-parity concepts.", "Contemporaneous weakness is not proof of a single causal driver."],
    ),
    "FX_INTERVENTION_TO_SPOT": TransmissionDefinition(
        transmission_id="FX_INTERVENTION_TO_SPOT",
        title="Official FX intervention and spot USD/JPY",
        summary="Credible yen-buying intervention directly changes the order-flow and policy signal facing the FX market.",
        trigger="Japan and a partner authority credibly signal or execute yen-buying intervention.",
        channels=[
            TransmissionChannel(label="Direct yen demand", description="Official purchases create immediate demand for yen and selling pressure on USD/JPY.", direction="downward pressure on USD/JPY"),
            TransmissionChannel(label="Policy signal", description="The willingness to act can change expectations about the acceptable range and future intervention risk.", direction="downward pressure on USD/JPY"),
            TransmissionChannel(label="Position adjustment", description="Short-yen positions may be reduced when a previously one-way trade becomes less attractive.", direction="amplification"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="Sterilisation or limited size", description="The lasting price effect may be smaller if the operation is temporary or limited relative to market turnover.", direction="dampening"),
            TransmissionChannel(label="Global dollar demand", description="Broad risk-off or U.S. rate moves can support the dollar at the same time.", direction="upward pressure on USD/JPY"),
        ],
        expected_relationship="Credible yen-buying intervention normally puts immediate downward pressure on USD/JPY, while the persistence of the move depends on credibility, size and competing macro forces.",
        limitations=["The framework supports a directional hypothesis rather than a guaranteed price move.", "Intervention timing, size and coordination may be uncertain until officially disclosed."],
    ),
    "RATE_DIFFERENTIAL_TO_FX": TransmissionDefinition(
        transmission_id="RATE_DIFFERENTIAL_TO_FX",
        title="Japan-U.S. rate differential and the yen",
        summary="A narrowing expected rate differential can reduce the incentive to hold short-yen carry positions, all else equal.",
        trigger="BOJ tightening expectations rise and Japanese yields increase relative to the expected U.S. policy path.",
        channels=[
            TransmissionChannel(label="Carry attractiveness", description="A smaller expected funding-cost advantage reduces the expected return from borrowing yen to buy higher-yielding assets.", direction="downward pressure on USD/JPY"),
            TransmissionChannel(label="Relative yields", description="Higher Japanese yields can increase demand for yen assets, subject to hedging and risk considerations.", direction="upward pressure on JPY"),
            TransmissionChannel(label="Position unwinding", description="Crowded short-yen positions become more vulnerable to stop-outs and deleveraging.", direction="amplification"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="U.S. yields", description="A simultaneous rise in U.S. yields can preserve or widen the differential.", direction="upward pressure on USD/JPY"),
            TransmissionChannel(label="Risk sentiment", description="Global risk aversion can change funding and safe-haven flows in competing directions.", direction="conditional"),
        ],
        expected_relationship="A narrowing expected rate differential generally supports a stronger yen, but FX is multi-causal and the net move can differ from the ceteris-paribus relationship.",
        limitations=["The rate differential is an important driver, not a complete FX model.", "Expectations and hedging costs matter in addition to spot yields."],
    ),
    "CARRY_UNWIND_FEEDBACK": TransmissionDefinition(
        transmission_id="CARRY_UNWIND_FEEDBACK",
        title="Carry-trade unwind feedback",
        summary="An initial yen rally can become larger when leveraged short-yen positions are reduced and closing them requires further yen buying.",
        trigger="A sharp yen move, intervention signal or rate-expectations shock makes crowded short-yen positions lose value.",
        channels=[
            TransmissionChannel(label="Mark-to-market loss", description="A yen appreciation creates an adverse FX translation move for a short-yen carry position.", direction="loss"),
            TransmissionChannel(label="Risk limits and margin", description="Losses can trigger stop-losses, margin calls or tighter risk limits.", direction="forced position reduction"),
            TransmissionChannel(label="Position closure", description="Buying yen to close short-yen exposure adds demand to the same market move.", direction="further yen appreciation"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="Liquidity and intervention response", description="Deep liquidity, official communication or new risk capital can slow the unwind.", direction="dampening"),
            TransmissionChannel(label="Carry income", description="Positive interest carry offsets a small part of the FX loss but is usually slow relative to a large spot shock.", direction="partial offset"),
        ],
        expected_relationship="The loop can amplify an initial yen rally, but it does not imply a fixed leverage or price-impact multiple.",
        limitations=["The size of the feedback depends on positioning, leverage, collateral terms and market liquidity.", "The mechanism is not evidence that every yen move is caused by carry unwinds."],
    ),
    "ENERGY_INFLATION_TO_YIELDS": TransmissionDefinition(
        transmission_id="ENERGY_INFLATION_TO_YIELDS",
        title="Energy inflation shock and nominal yields",
        summary="A sharp energy move can lift inflation risk and alter the expected path of policy rates, putting upward pressure on nominal yields.",
        trigger="Oil prices rise materially and the market revises its inflation outlook higher.",
        channels=[
            TransmissionChannel(label="Inflation compensation", description="Higher expected inflation can raise the inflation component embedded in nominal yields.", direction="upward pressure on nominal yields"),
            TransmissionChannel(label="Policy expectations", description="Markets may price a more restrictive central-bank path or fewer expected cuts.", direction="upward pressure on front-end yields"),
            TransmissionChannel(label="Term premium and supply", description="Fiscal issuance, duration supply and uncertainty can add pressure at the long end.", direction="upward pressure on long yields"),
        ],
        countervailing_channels=[
            TransmissionChannel(label="Growth destruction", description="A persistent energy shock can weaken demand and eventually pull expected real rates lower.", direction="downward pressure"),
            TransmissionChannel(label="Safe-haven demand", description="A broader risk-off episode can create demand for high-quality government bonds.", direction="downward pressure"),
        ],
        expected_relationship="An energy-driven inflation shock generally supports higher nominal yields in the near term, although the curve response can differ by maturity.",
        limitations=["The effect depends on whether the shock is viewed as persistent and on the central-bank reaction function.", "A parallel yield move should not be assumed from the mechanism alone."],
    ),
    "INFLATION_TO_POLICY_EXPECTATIONS": TransmissionDefinition(
        transmission_id="INFLATION_TO_POLICY_EXPECTATIONS",
        title="Inflation surprise and policy expectations",
        summary="An inflation surprise can change the expected path of central-bank policy and the pricing of rates instruments.",
        trigger="Inflation data arrives above or below the market's prior expectation.",
        channels=[
            TransmissionChannel(label="Policy path", description="Markets revise the expected policy-rate path in response to the inflation signal.", direction="conditional"),
            TransmissionChannel(label="Real-rate response", description="The effect on real yields depends on how nominal rates and inflation expectations move together.", direction="conditional"),
        ],
        countervailing_channels=[TransmissionChannel(label="Growth concern", description="A weak growth backdrop can limit the expected policy response.", direction="downward pressure on yields")],
        expected_relationship="The surprise changes expectations; it does not uniquely determine the realized yield move.",
        limitations=["The market response depends on the surprise relative to expectations, not the level alone.", "The relationship is conditional and time-varying."],
    ),
    "LDI_DELEVERAGING_LOOP": TransmissionDefinition(
        transmission_id="LDI_DELEVERAGING_LOOP",
        title="LDI leverage and liquidity feedback loop",
        summary="A first-order yield shock can be amplified by collateral calls, forced selling and deteriorating market liquidity.",
        trigger="Long-duration positions lose value in a leveraged liability-driven investment structure.",
        channels=[
            TransmissionChannel(label="Initial yield shock", description="Long-duration assets lose value as yields rise.", direction="loss"),
            TransmissionChannel(label="Collateral calls", description="The loss creates additional collateral or margin needs.", direction="upward pressure on cash demand"),
            TransmissionChannel(label="Forced sales", description="Funds sell liquid assets to raise cash or reduce leverage.", direction="downward pressure on prices"),
            TransmissionChannel(label="Liquidity deterioration", description="Sales into a stressed market can worsen execution and create a further price/yield move.", direction="amplification"),
        ],
        countervailing_channels=[TransmissionChannel(label="Deleveraging and intervention", description="Position reduction, additional collateral and official intervention can slow the feedback loop.", direction="stabilising")],
        expected_relationship="The mechanism explains why realized stress can materially exceed a simple macro first-order estimate; it does not provide a fixed amplification multiple.",
        limitations=["The strength and timing of the loop depend on leverage, collateral terms, liquidity and market positioning.", "This is a market-structure explanation, not a deterministic crisis forecast."],
    ),
    "YIELD_TO_BOND_PRICE": TransmissionDefinition(
        transmission_id="YIELD_TO_BOND_PRICE",
        title="Yield move to bond price",
        summary="Fixed-rate bond prices and yields generally move in opposite directions.",
        trigger="The market yield used to discount a fixed-rate bond changes.",
        channels=[TransmissionChannel(label="Discounting", description="A higher discount rate reduces the present value of future fixed cash flows.", direction="inverse price/yield relationship")],
        countervailing_channels=[TransmissionChannel(label="Convexity", description="The relationship is curved, so the local duration estimate changes as the shock becomes larger.", direction="adjustment")],
        expected_relationship="A higher yield generally implies a lower bond price; duration determines the approximate first-order sensitivity.",
        limitations=["Duration is a local approximation and does not capture every instrument feature or liquidity effect."],
    ),
}


_STATISTICAL_MODELS: dict[str, dict[str, Any]] = {
    "PORTFOLIO_VOLATILITY_MODEL": {
        "title": "Covariance-based portfolio volatility",
        "summary": "Estimate portfolio volatility from weights, individual volatilities and co-movement.",
        "model": "sigma_p = sqrt(w^T Sigma w)",
        "inputs": ["portfolio weights", "asset volatilities", "correlation or covariance matrix"],
        "assumptions": ["The input window is representative of the risk horizon.", "Covariance and volatility estimates are internally consistent."],
        "limitations": ["This is a statistical estimate, not a deterministic fact.", "Correlations and volatility can change during stress."],
    },
    "REGRESSION_RELATIONSHIP": {
        "title": "Regression relationship",
        "summary": "Estimate an average conditional relationship between a dependent variable and selected explanatory variables.",
        "model": "y_t = alpha + beta x_t + error_t",
        "inputs": ["dependent series", "explanatory series", "sample window", "model specification"],
        "assumptions": ["The specification is appropriate for the question and sample.", "Residual and parameter diagnostics are reviewed."],
        "limitations": ["Association is not proof of causation.", "Parameter estimates are sample-dependent and uncertain."],
    },
}


_IDENTITIES: dict[str, dict[str, Any]] = {
    "NOMINAL_YIELD_DECOMPOSITION": {
        "title": "Nominal yield decomposition",
        "summary": "Nominal yield can be discussed as expected real rates, expected inflation and a term premium.",
        "formula": "Nominal yield approximately equals expected real rate plus expected inflation plus term premium.",
        "limitations": ["Conceptual decomposition only; components are estimated and not directly observed as a single exact identity in the case."],
    }
}


_RULES_OF_THUMB: dict[str, dict[str, Any]] = {
    "ONE_BP_IS_0001": {
        "title": "Basis-point convention",
        "summary": "One basis point is one hundredth of a percentage point, or 0.0001 in decimal yield terms.",
        "rule": "1 bp = 0.01% = 0.0001",
        "limitations": ["This is a unit convention, not a statement about how markets will move."],
    }
}


def _normalized_support(value: AnalyticalSupport | dict[str, Any]) -> AnalyticalSupport:
    return value if isinstance(value, AnalyticalSupport) else AnalyticalSupport.model_validate(value)


def _protected_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return normalized in {
        "actual", "actualvalue", "actualdirection", "actualoutcome", "actualmarketmoves",
        "realized", "realizedvalue", "futureobservation", "futureobservations", "postreveal",
    } or normalized.startswith("actual") or normalized.startswith("realized") or normalized.startswith("futureobservation")


def _contains_protected_data(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_protected_key(str(key)) or _contains_protected_data(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_protected_data(item) for item in value)
    return False


def validate_analytical_support(value: AnalyticalSupport | dict[str, Any]) -> AnalyticalSupport:
    support = _normalized_support(value)
    if support.type != "none" and not support.reference_id:
        raise ValueError(f"Analytical support type '{support.type}' requires a reference_id.")
    if support.available_before_reveal and _contains_protected_data(value.model_dump() if isinstance(value, AnalyticalSupport) else value):
        raise ValueError("Before-reveal analytical support cannot contain protected actual or post-reveal data.")
    if support.type == "formula":
        get_formula_definition(support.reference_id or "")
    elif support.type == "transmission":
        if support.reference_id not in _TRANSMISSIONS:
            raise ValueError(f"Transmission not found: {support.reference_id}")
    elif support.type == "statistical_model":
        if support.reference_id not in _STATISTICAL_MODELS:
            raise ValueError(f"Statistical model not found: {support.reference_id}")
    elif support.type == "identity":
        if support.reference_id not in _IDENTITIES:
            raise ValueError(f"Identity not found: {support.reference_id}")
    elif support.type == "rule_of_thumb":
        if support.reference_id not in _RULES_OF_THUMB:
            raise ValueError(f"Rule of thumb not found: {support.reference_id}")
    return support


def get_analytical_support(support_type: str, reference_id: str, *, available_before_reveal: bool = True) -> AnalyticalSupportDefinition:
    try:
        normalized_type: AnalyticalSupportType = support_type  # type: ignore[assignment]
        if normalized_type == "formula":
            formula = get_formula_definition(reference_id)
            return AnalyticalSupportDefinition(support_type=normalized_type, reference_id=reference_id, title=formula.name, summary=formula.plain_english, available_before_reveal=available_before_reveal, formula=formula.model_dump())
        if normalized_type == "transmission":
            transmission = _TRANSMISSIONS[reference_id]
            return AnalyticalSupportDefinition(support_type=normalized_type, reference_id=reference_id, title=transmission.title, summary=transmission.summary, available_before_reveal=available_before_reveal, transmission=transmission)
        if normalized_type == "statistical_model":
            model = _STATISTICAL_MODELS[reference_id]
            return AnalyticalSupportDefinition(support_type=normalized_type, reference_id=reference_id, title=model["title"], summary=model["summary"], available_before_reveal=available_before_reveal, model=model)
        if normalized_type == "identity":
            identity = _IDENTITIES[reference_id]
            return AnalyticalSupportDefinition(support_type=normalized_type, reference_id=reference_id, title=identity["title"], summary=identity["summary"], available_before_reveal=available_before_reveal, identity=identity)
        if normalized_type == "rule_of_thumb":
            rule = _RULES_OF_THUMB[reference_id]
            return AnalyticalSupportDefinition(support_type=normalized_type, reference_id=reference_id, title=rule["title"], summary=rule["summary"], available_before_reveal=available_before_reveal, rule_of_thumb=rule)
    except KeyError as exc:
        raise ValueError(f"Analytical support not found: {support_type}/{reference_id}") from exc
    raise ValueError(f"Analytical support type '{support_type}' is not referenceable.")


def list_transmissions() -> list[TransmissionDefinition]:
    return list(_TRANSMISSIONS.values())
