from __future__ import annotations
from typing import Tuple
import numpy as np
import pandas as pd


_NUMERIC_COLS = [
    "size_m_or_units", "weight_kg", "quality_grade", "design_complexity",
    "raw_material_cost_inr", "labour_cost_inr",
    "inbound_procurement_cost_inr", "production_overhead_inr",
    "material_price_latest", "material_trend_30d_pct",
    "odop_state_product_count", "odop_state_gi_count", "odop_state_sector_count",
    "ec_purchase_rate", "ec_avg_unit_price",
    "demand_index",
    "market_median", "market_min", "market_max", "market_mean",
    "mrp_median", "discount_pct_median",
    "seller_count_median", "rating_median",
    "comparable_count", "market_dispersion",
    "trend_7d_pct", "trend_30d_pct", "trend_90d_pct",
]

_CATEGORICAL_COLS = [
    "category", "craft_type", "material", "state", "district", "season",
]

TARGET_COL = "selling_price_inr"
FEATURE_COLUMNS = _NUMERIC_COLS + _CATEGORICAL_COLS


def impute_numeric_missing(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    out = df.copy()
    for c in columns:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
            med = out[c].median()
            if pd.isna(med):
                med = 0.0
            out[c] = out[c].fillna(med).astype(np.float32)
    return out


def impute_categorical_missing(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    out = df.copy()
    for c in columns:
        if c in out.columns:
            mode = out[c].mode(dropna=True)
            fill = mode.iloc[0] if not mode.empty else "__missing__"
            out[c] = out[c].fillna(fill).astype(str)
    return out


def align_categoricals(df: pd.DataFrame, levels: dict) -> pd.DataFrame:
    out = df.copy()
    for c, lvl in levels.items():
        if c not in out.columns:
            continue
        out[c] = out[c].astype(str)
        known = set(lvl)
        out[c] = out[c].where(out[c].isin(known), other="__missing__")
        out[c] = pd.Categorical(out[c], categories=lvl)
    return out


def add_missing_flags(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    out = df.copy()
    for c in columns:
        if c in out.columns:
            out[f"{c}_isna"] = pd.to_numeric(out[c], errors="coerce").isna().astype(np.int8)
    return out


def build_feature_matrix(market_df: pd.DataFrame) -> pd.DataFrame:
    df = market_df.copy()
    if "comparable_count" not in df.columns:
        df["comparable_count"] = 0
    if "market_dispersion" not in df.columns:
        df["market_dispersion"] = 0.0
    for col in _NUMERIC_COLS:
        if col not in df.columns:
            df[col] = np.nan
    for col in _CATEGORICAL_COLS:
        if col not in df.columns:
            df[col] = "__missing__"
    df = add_missing_flags(df, _NUMERIC_COLS)
    df = impute_numeric_missing(df, _NUMERIC_COLS)
    df = impute_categorical_missing(df, _CATEGORICAL_COLS)
    for col in _NUMERIC_COLS:
        df[col] = df[col].astype(np.float32)
    for col in _CATEGORICAL_COLS:
        df[col] = df[col].astype("category")
    return df[FEATURE_COLUMNS]


def split_train_val_test(
    X: pd.DataFrame, y: pd.Series, seed: int = 42, val_frac: float = 0.15, test_frac: float = 0.15
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    n = len(X)
    perm = rng.permutation(n)
    n_test = int(n * test_frac)
    n_val = int(n * val_frac)
    test_idx = perm[:n_test]
    val_idx = perm[n_test:n_test + n_val]
    train_idx = perm[n_test + n_val:]
    return (
        X.iloc[train_idx],
        y.iloc[train_idx],
        X.iloc[val_idx],
        y.iloc[val_idx],
        X.iloc[test_idx],
        y.iloc[test_idx],
    )
