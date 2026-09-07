from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd


class BaselineValidationError(ValueError):
    pass


def cost_plus_baseline(cost_floor: float, margin: float = 1.5) -> float:
    if margin < 1.0:
        raise BaselineValidationError(f"margin must be >= 1.0, got {margin}")
    return float(cost_floor) * float(margin)


def market_median_baseline(market_median) -> Optional[float]:
    if market_median is None:
        return None
    return float(market_median)


def category_median_margin(market_df: pd.DataFrame) -> dict:
    valid = market_df[(market_df["selling_price_inr"] > 0) & (market_df["cost_floor_inr"] > 0)].copy()
    valid["margin"] = valid["selling_price_inr"] / valid["cost_floor_inr"]
    return valid.groupby("category", observed=True)["margin"].median().to_dict()


def apply_cost_plus_baseline(market_df: pd.DataFrame, margins: Optional[dict] = None) -> np.ndarray:
    if margins is None:
        margins = category_median_margin(market_df)
    default = float(np.median(list(margins.values()))) if margins else 1.5
    out = []
    for _, row in market_df.iterrows():
        m = float(margins.get(row["category"], default))
        if m < 1.0:
            m = 1.5
        out.append(float(row["cost_floor_inr"]) * m)
    return np.asarray(out, dtype=np.float64)


def apply_market_median_baseline(market_df: pd.DataFrame) -> np.ndarray:
    valid = market_df[market_df["selling_price_inr"] > 0]
    g = valid.groupby(["category", "material", "state"], observed=True)["selling_price_inr"].median()
    out = []
    for _, row in market_df.iterrows():
        try:
            v = float(g.loc[(row["category"], row["material"], row["state"])])
        except KeyError:
            v = float(row["cost_floor_inr"]) * 1.5
        out.append(v)
    return np.asarray(out, dtype=np.float64)
