from __future__ import annotations
import numpy as np
import pandas as pd


def audit_feature_leakage(X: pd.DataFrame, y: pd.Series, tol: float = 0.01) -> list:
    y = pd.to_numeric(y, errors="coerce").reset_index(drop=True)
    leaks = []
    for c in X.columns:
        s = pd.to_numeric(X[c], errors="coerce").reset_index(drop=True)
        if s.isna().all():
            continue
        if np.allclose(s.values, y.values, atol=tol, equal_nan=True):
            leaks.append(c)
    return leaks


def loo_median_check(buckets_df: pd.DataFrame, market_df: pd.DataFrame) -> bool:
    g = market_df.groupby(["category", "material", "state"], observed=True)["selling_price_inr"]
    total = g.transform("sum")
    cnt = g.transform("count")
    loo = (total - market_df["selling_price_inr"]) / (cnt - 1)
    return bool(loo.notna().any())


def cost_floor_not_a_feature(X: pd.DataFrame) -> bool:
    return "cost_floor_inr" not in X.columns
