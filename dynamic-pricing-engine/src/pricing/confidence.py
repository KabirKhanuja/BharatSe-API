from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ReliabilityInputs:
    comparable_count: int
    feature_completeness: float
    data_recency_days: int
    market_dispersion: float
    interval_width_ratio: float


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def compute_reliability_score(inputs: ReliabilityInputs) -> int:
    comparable_score = _clip(inputs.comparable_count / 50.0)

    feature_score = _clip(inputs.feature_completeness)

    recency_score = _clip(1.0 - (inputs.data_recency_days / 90.0))

    dispersion_score = _clip(1.0 - inputs.market_dispersion)

    interval_score = _clip(1.0 - inputs.interval_width_ratio)

    weights = {
        "comparable": 0.40,
        "feature": 0.20,
        "recency": 0.15,
        "dispersion": 0.15,
        "interval": 0.10,
    }
    total = (
        weights["comparable"] * comparable_score
        + weights["feature"] * feature_score
        + weights["recency"] * recency_score
        + weights["dispersion"] * dispersion_score
        + weights["interval"] * interval_score
    )
    return int(round(_clip(total) * 100))
