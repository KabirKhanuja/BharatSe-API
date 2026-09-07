from __future__ import annotations
from typing import Any
import math
import numpy as np
import pandas as pd

from src.pricing.cost_engine import cost_floor
from src.pricing.policy import (
    apply_cost_floor,
    apply_market_sanity,
    apply_insufficient_data,
    apply_outlier_guard,
)


_CATEGORICAL_COLS = [
    "category", "craft_type", "material", "state", "district", "season",
]


def _request_row(request: dict, categorical_levels: dict | None) -> pd.DataFrame:
    cols = [
        "size_m_or_units", "weight_kg", "quality_grade", "design_complexity",
        "raw_material_cost_inr", "labour_cost_inr",
        "inbound_procurement_cost_inr", "production_overhead_inr",
        "category", "craft_type", "material", "state", "district", "season",
        "comparable_count", "market_dispersion",
        "material_price_latest", "material_trend_30d_pct",
        "odop_state_product_count", "odop_state_gi_count", "odop_state_sector_count",
        "ec_purchase_rate", "ec_avg_unit_price", "demand_index",
        "market_median", "market_min", "market_max", "market_mean",
        "mrp_median", "discount_pct_median",
        "seller_count_median", "rating_median",
        "trend_7d_pct", "trend_30d_pct", "trend_90d_pct",
    ]
    row = {c: request.get(c, np.nan) for c in cols}
    if "season" in request and request["season"] is not None:
        row["season"] = request["season"]
    df = pd.DataFrame([row])

    if categorical_levels:
        for c in _CATEGORICAL_COLS:
            if c in df.columns and c in categorical_levels:
                levels = list(categorical_levels[c])
                df[c] = df[c].astype(str)
                df[c] = df[c].where(df[c].isin(levels), other="__missing__")
                df[c] = pd.Categorical(df[c], categories=levels)
    return df


def _safe_float(x) -> float:
    if x is None:
        return float("nan")
    try:
        v = float(x)
    except (TypeError, ValueError):
        return float("nan")
    return v


def predict_price(request: dict, artifacts: dict) -> dict:
    categorical_levels = artifacts.get("categorical_levels")
    X = _request_row(request, categorical_levels)
    p50_model = artifacts["p50"]
    p10_model = artifacts["p10"]
    p50q_model = artifacts["p50_quantile"]
    p90_model = artifacts["p90"]
    buckets = artifacts.get("market_buckets")

    p10_pred = float(p10_model.predict(X)[0])
    p50_pred = float(p50q_model.predict(X)[0])
    p90_pred = float(p90_model.predict(X)[0])
    p50_reg = float(p50_model.predict(X)[0])

    s10, s50, s90 = (p10_pred, p50_pred, p90_pred)
    s10 = min(s10, s50)
    s90 = max(s90, s50)

    cost_floor_value = cost_floor(
        request.get("raw_material_cost_inr", 0.0),
        request.get("labour_cost_inr", 0.0),
        request.get("inbound_procurement_cost_inr", 0.0),
        request.get("production_overhead_inr", 0.0),
    )

    market_median = request.get("market_median")
    if market_median is None:
        try:
            from src.features.market_features import get_comparable_stats
            stats = get_comparable_stats(
                buckets,
                request["category"],
                request["material"],
                request["state"],
            )
            market_median = float(stats["market_median"])
        except Exception:
            market_median = None

    comparable_count = int(request.get("comparable_count", 0) or 0)
    if market_median is not None and comparable_count == 0:
        comparable_count = 1

    recommended = apply_cost_floor(price=s50, cost_floor_value=cost_floor_value)
    s10 = max(s10, recommended.adjusted_price)
    s90 = max(s90, recommended.adjusted_price)

    flags = list(recommended.flags)

    market_p10 = request.get("market_p10") or s10
    market_p90 = request.get("market_p90") or s90
    sane = apply_market_sanity(price=recommended.adjusted_price, market_p10=market_p10, market_p90=market_p90)
    flags.extend(sane.flags)

    insufficient = apply_insufficient_data(
        price=recommended.adjusted_price,
        cost_floor_value=cost_floor_value,
        comparable_count=comparable_count,
    )
    flags.extend(insufficient.flags)

    outlier = apply_outlier_guard(
        price=recommended.adjusted_price,
        market_median=_safe_float(market_median),
        comparable_count=comparable_count,
    )
    flags.extend(outlier.flags)

    final = float(sane.adjusted_price)
    if final < cost_floor_value:
        final = float(cost_floor_value)

    p10_out = float(s10)
    p90_out = float(s90)
    if p10_out > final:
        p10_out = final
    if p90_out < final:
        p90_out = final

    return {
        "p10": p10_out,
        "p50": final,
        "p90": p90_out,
        "recommended_price": final,
        "cost_floor": float(cost_floor_value),
        "market_median": _safe_float(market_median),
        "comparable_count": comparable_count,
        "flags": flags,
    }
