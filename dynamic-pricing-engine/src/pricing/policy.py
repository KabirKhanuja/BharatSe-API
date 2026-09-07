from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


class PolicyValidationError(ValueError):
    pass


@dataclass
class PolicyResult:
    adjusted_price: float
    flags: List[str] = field(default_factory=list)


def apply_cost_floor(price: float, cost_floor_value: float) -> PolicyResult:
    if price < cost_floor_value:
        return PolicyResult(adjusted_price=float(cost_floor_value), flags=["cost_floor_lift"])
    return PolicyResult(adjusted_price=float(price), flags=[])


def apply_market_sanity(
    price: float,
    market_p10: Optional[float],
    market_p90: Optional[float],
) -> PolicyResult:
    if market_p10 is None or market_p90 is None:
        return PolicyResult(adjusted_price=float(price), flags=[])
    if price < market_p10:
        return PolicyResult(adjusted_price=float(market_p10), flags=["market_sanity_clipped_low"])
    if price > market_p90:
        return PolicyResult(adjusted_price=float(market_p90), flags=["market_sanity_clipped_high"])
    return PolicyResult(adjusted_price=float(price), flags=[])


def apply_insufficient_data(
    price: float,
    cost_floor_value: float,
    comparable_count: int,
    margin: float = 1.5,
) -> PolicyResult:
    if margin < 1.0:
        raise PolicyValidationError(f"margin must be >= 1.0, got {margin}")
    if comparable_count > 0:
        return PolicyResult(adjusted_price=float(price), flags=[])
    target = float(cost_floor_value) * float(margin)
    return PolicyResult(adjusted_price=target, flags=["insufficient_comparables"])


def apply_outlier_guard(
    price: float,
    market_median: Optional[float],
    comparable_count: int,
    single_seller_threshold: int = 5,
) -> PolicyResult:
    if market_median is None:
        return PolicyResult(adjusted_price=float(price), flags=[])
    if comparable_count >= single_seller_threshold:
        return PolicyResult(adjusted_price=float(price), flags=[])
    if comparable_count <= 0:
        return PolicyResult(adjusted_price=float(price), flags=[])
    widened = max(float(price), float(market_median) * 1.05)
    return PolicyResult(adjusted_price=widened, flags=["single_seller_risk"])
