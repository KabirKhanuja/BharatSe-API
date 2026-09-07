from __future__ import annotations
from numbers import Number


class CostValidationError(ValueError):
    pass


def _coerce(name: str, value, allow_none: bool = True) -> float:
    if value is None:
        if allow_none:
            return 0.0
        raise CostValidationError(f"{name} must be a number, got None")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CostValidationError(f"{name} must be numeric, got {type(value).__name__}")
    v = float(value)
    if v < 0:
        raise CostValidationError(f"{name} must be non-negative, got {v}")
    return v


def cost_floor(
    raw_material_cost_inr=None,
    labour_cost_inr=None,
    inbound_procurement_cost_inr=None,
    production_overhead_inr=None,
) -> float:
    rm = _coerce("raw_material_cost_inr", raw_material_cost_inr)
    lb = _coerce("labour_cost_inr", labour_cost_inr)
    ip = _coerce("inbound_procurement_cost_inr", inbound_procurement_cost_inr)
    ov = _coerce("production_overhead_inr", production_overhead_inr)
    return round(rm + lb + ip + ov, 2)
