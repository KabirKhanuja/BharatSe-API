from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd

from src.features.market_features import (
    get_comparable_stats,
    InsufficientComparablesError,
)
from src.features.material_features import (
    lookup_material_trend,
    UnknownMaterialError,
)


@dataclass
class InferenceRequest:
    category: str
    craft_type: str
    material: str
    state: str
    district: str
    size_m_or_units: float
    weight_kg: float
    handmade: bool
    quality_grade: int
    design_complexity: int
    raw_material_cost_inr: float
    labour_cost_inr: float
    inbound_procurement_cost_inr: float
    production_overhead_inr: float
    season: str | None = None


def assemble_inference_features(
    request: InferenceRequest,
    market_buckets: pd.DataFrame,
    category_aggregates: pd.DataFrame,
    state_aggregates: pd.DataFrame,
    material_trend: pd.DataFrame,
) -> dict:
    cost_floor = (
        float(request.raw_material_cost_inr)
        + float(request.labour_cost_inr)
        + float(request.inbound_procurement_cost_inr)
        + float(request.production_overhead_inr)
    )

    try:
        stats = get_comparable_stats(market_buckets, request.category, request.material, request.state)
        market_median = float(stats["market_median"])
        market_min = float(stats["market_min"])
        market_max = float(stats["market_max"])
        market_mean = float(stats["market_mean"])
        mrp_median = float(stats["mrp_median"])
        discount_pct_median = float(stats["discount_pct_median"])
        seller_count_median = float(stats["seller_count_median"])
        rating_median = float(stats["rating_median"])
        comparable_count = int(stats["comparable_count"])
        market_dispersion = (
            (stats.get("market_p75", market_max) - stats.get("market_p25", market_min)) / market_median
            if comparable_count > 0 and market_median > 0
            else 0.0
        )
    except InsufficientComparablesError:
        market_median = None
        market_min = None
        market_max = None
        market_mean = None
        mrp_median = None
        discount_pct_median = None
        seller_count_median = None
        rating_median = None
        comparable_count = 0
        market_dispersion = 0.0

    try:
        m = lookup_material_trend(material_trend, request.state, request.material)
        material_price_latest = m["material_price_latest"]
        material_trend_30d_pct = m["material_trend_30d_pct"]
    except UnknownMaterialError:
        material_price_latest = None
        material_trend_30d_pct = None

    state_row = state_aggregates.loc[request.state] if request.state in state_aggregates.index else None
    if state_row is not None:
        odop_state_product_count = int(state_row["odop_state_product_count"])
        odop_state_gi_count = int(state_row["odop_state_gi_count"])
        odop_state_sector_count = int(state_row["odop_state_sector_count"])
    else:
        odop_state_product_count = 0
        odop_state_gi_count = 0
        odop_state_sector_count = 0

    if category_aggregates is not None and len(category_aggregates) > 0:
        ec_purchase_rate = float(category_aggregates["ec_purchase_rate"].mean())
        ec_avg_unit_price = float(category_aggregates["ec_avg_unit_price"].mean())
        demand_index = max(0.0, min(1.0, ec_purchase_rate))
    else:
        ec_purchase_rate = None
        ec_avg_unit_price = None
        demand_index = None

    return {
        "category": request.category,
        "craft_type": request.craft_type,
        "material": request.material,
        "state": request.state,
        "district": request.district,
        "size_m_or_units": float(request.size_m_or_units),
        "weight_kg": float(request.weight_kg),
        "handmade": int(bool(request.handmade)),
        "quality_grade": int(request.quality_grade),
        "design_complexity": int(request.design_complexity),
        "season": request.season,

        "raw_material_cost_inr": float(request.raw_material_cost_inr),
        "labour_cost_inr": float(request.labour_cost_inr),
        "inbound_procurement_cost_inr": float(request.inbound_procurement_cost_inr),
        "production_overhead_inr": float(request.production_overhead_inr),
        "cost_floor_inr": cost_floor,

        "market_median": market_median,
        "market_min": market_min,
        "market_max": market_max,
        "market_mean": market_mean,
        "mrp_median": mrp_median,
        "discount_pct_median": discount_pct_median,
        "seller_count_median": seller_count_median,
        "rating_median": rating_median,
        "comparable_count": comparable_count,
        "market_dispersion": float(market_dispersion) if market_dispersion is not None and not (isinstance(market_dispersion, float) and math.isnan(market_dispersion)) else 0.0,

        "material_price_latest": material_price_latest,
        "material_trend_30d_pct": material_trend_30d_pct,

        "odop_state_product_count": odop_state_product_count,
        "odop_state_gi_count": odop_state_gi_count,
        "odop_state_sector_count": odop_state_sector_count,

        "ec_purchase_rate": ec_purchase_rate,
        "ec_avg_unit_price": ec_avg_unit_price,
        "demand_index": demand_index,

        "trend_7d_pct": None,
        "trend_30d_pct": None,
        "trend_90d_pct": None,
    }
