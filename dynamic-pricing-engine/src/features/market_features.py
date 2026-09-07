from __future__ import annotations
import numpy as np
import pandas as pd


class InsufficientComparablesError(KeyError):
    pass


_BUCKET_AGG = {
    "selling_price_inr": ["median", "min", "max", "mean", "count"],
    "mrp_inr": "median",
    "discount_pct": "median",
    "seller_count": "median",
    "rating": "median",
}

_BUCKET_OUT_COLS = {
    ("selling_price_inr", "median"): "market_median",
    ("selling_price_inr", "min"): "market_min",
    ("selling_price_inr", "max"): "market_max",
    ("selling_price_inr", "mean"): "market_mean",
    ("selling_price_inr", "count"): "comparable_count",
    ("mrp_inr", "median"): "mrp_median",
    ("discount_pct", "median"): "discount_pct_median",
    ("seller_count", "median"): "seller_count_median",
    ("rating", "median"): "rating_median",
}


def build_market_buckets(df: pd.DataFrame) -> pd.DataFrame:
    valid = df[df["selling_price_inr"] > 0]
    g = valid.groupby(["category", "material", "state"], observed=True).agg(_BUCKET_AGG)
    g.columns = [_BUCKET_OUT_COLS.get(c, "_".join(c)) for c in g.columns]
    q = (
        valid.groupby(["category", "material", "state"], observed=True)["selling_price_inr"]
        .quantile([0.25, 0.75])
        .unstack()
    )
    q.columns = ["market_p25", "market_p75"]
    buckets = g.join(q)
    for col in ("market_median", "market_min", "market_max", "market_mean"):
        buckets[col] = buckets[col].astype(float)
    return buckets


def get_comparable_stats(buckets: pd.DataFrame, category: str, material: str, state: str) -> dict:
    try:
        row = buckets.loc[(category, material, state)]
    except KeyError as e:
        raise InsufficientComparablesError(
            f"No comparable products for ({category!r}, {material!r}, {state!r})"
        ) from e
    return row.to_dict()


def compute_dispersion(values: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce").dropna()
    if v.empty:
        return 0.0
    m = float(v.mean())
    if m == 0:
        return 0.0
    return float(v.std(ddof=0) / m)


def leave_one_out_median(df: pd.DataFrame, group_cols: list, value_col: str) -> pd.Series:
    valid = df[df[value_col] > 0]
    g = valid.groupby(group_cols, observed=True)[value_col]
    total = g.transform("sum")
    cnt = g.transform("count")
    return (total - df[value_col]) / (cnt - 1)
