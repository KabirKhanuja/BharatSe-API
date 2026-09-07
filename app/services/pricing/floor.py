"""The wage floor.

This is deliberately arithmetic and not learned. A model trained on market
prices learns what artisans are currently paid, which is the thing the whole
programme exists to change. So the floor is computed, the model only ever
proposes a price above it, and the floor is the number we can defend.
"""

from dataclasses import dataclass

from app.core.config import settings

# Rough overhead on top of materials and labour: packaging, wastage, the share
# of a tool or dye bath that this piece consumed.
OVERHEAD_RATE = 0.12


@dataclass(frozen=True)
class FloorBreakdown:
    """Every component is returned so the app can show its working."""

    material_cost: int
    labour_cost: int
    overhead: int
    floor: int
    wage_per_hour: int
    hours: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "material_cost": self.material_cost,
            "labour_cost": self.labour_cost,
            "overhead": self.overhead,
            "floor": self.floor,
            "wage_per_hour": self.wage_per_hour,
            "hours": self.hours,
        }


def compute_floor(
    material_cost: int,
    hours_of_work: float,
    wage_per_hour: int | None = None,
) -> FloorBreakdown:
    """Lowest price at which this piece does not underpay its maker.

    `hours_of_work` comes from the artisan herself rather than being estimated,
    which is why the app makes it an editable field rather than a hidden one.
    """
    if material_cost < 0:
        raise ValueError("material_cost cannot be negative")
    if hours_of_work < 0:
        raise ValueError("hours_of_work cannot be negative")

    wage = wage_per_hour or settings.FAIR_WAGE_PER_HOUR
    labour = round(hours_of_work * wage)
    overhead = round((material_cost + labour) * OVERHEAD_RATE)

    return FloorBreakdown(
        material_cost=material_cost,
        labour_cost=labour,
        overhead=overhead,
        floor=material_cost + labour + overhead,
        wage_per_hour=wage,
        hours=hours_of_work,
    )
