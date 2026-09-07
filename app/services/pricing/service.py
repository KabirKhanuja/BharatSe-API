"""Puts the three pricing layers together.

Layer one is the wage floor, which is arithmetic and non negotiable.
Layer two is the learned band from LightGBM.
Layer three reconciles them, and the floor always wins.
"""

from dataclasses import dataclass

from app.core.logging import get_logger
from app.services.pricing.features import PriceInput
from app.services.pricing.floor import FloorBreakdown, compute_floor
from app.services.pricing.model import PriceBandModel

log = get_logger(__name__)

_model = PriceBandModel()


@dataclass
class PriceSuggestion:
    p10: int
    p50: int
    p90: int
    floor: int
    breakdown: FloorBreakdown
    model_used: bool
    lifted_to_floor: bool
    note: str


def _fallback_band(floor: int) -> tuple[int, int, int]:
    """Used before the model is trained, and if loading it fails.

    A markup on the floor. Honest, explainable, and never below cost, which is
    better than refusing to answer while an artisan waits on a bad connection.
    """
    return round(floor * 1.25), round(floor * 1.55), round(floor * 2.0)


def suggest_price(
    item: PriceInput,
    wage_per_hour: int | None = None,
) -> PriceSuggestion:
    breakdown = compute_floor(item.material_cost, item.hours_of_work, wage_per_hour)
    floor = breakdown.floor

    model_used = False
    try:
        p10, p50, p90 = (int(round(v)) for v in _model.predict([item])[0])
        model_used = True
    except (FileNotFoundError, ImportError, ValueError, OSError) as exc:
        # OSError matters as much as the others. LightGBM's wheel does not
        # bundle libomp, so on a machine without it `import lightgbm` fails at
        # dlopen. Pricing must degrade to the cost based band rather than
        # returning a 500 while an artisan waits.
        log.warning("price_model_unavailable", error=str(exc))
        p10, p50, p90 = _fallback_band(floor)

    # The whole ethical position in three lines. The market may push a price
    # up. Nothing in this system can push it below the maker's wage.
    lifted = p10 < floor
    p10 = max(p10, floor)
    p50 = max(p50, p10)
    p90 = max(p90, p50)

    note = (
        "Raised to the fair wage floor"
        if lifted
        else ("Based on comparable sales" if model_used else "Based on cost and a standard margin")
    )

    return PriceSuggestion(
        p10=p10,
        p50=p50,
        p90=p90,
        floor=floor,
        breakdown=breakdown,
        model_used=model_used,
        lifted_to_floor=lifted,
        note=note,
    )


def validate_price(price: int, material_cost: int, hours_of_work: float) -> int:
    """Reject a price below the floor. Called before a listing is published."""
    from app.core.errors import BelowWageFloorError

    floor = compute_floor(material_cost, hours_of_work).floor
    if price < floor:
        raise BelowWageFloorError(
            f"A price of {price} is below the fair wage floor of {floor} "
            f"for {hours_of_work} hours of work."
        )
    return price
