from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data.loaders import load_synthetic_market
from src.features.market_features import build_market_buckets, leave_one_out_median
from src.models.preprocessing import build_feature_matrix
from src.models.diagnostics import (
    audit_feature_leakage,
    loo_median_check,
    cost_floor_not_a_feature,
)


def test_audit_feature_leakage_finds_exact_match():
    X = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    y = pd.Series([1.0, 2.0, 3.0])
    leaks = audit_feature_leakage(X, y, tol=0.01)
    assert "a" in leaks
    assert "b" not in leaks


def test_audit_feature_leakage_clean_on_real_matrix(synthetic_market_csv: Path):
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    y = market["selling_price_inr"].astype(float)
    leaks = audit_feature_leakage(X, y, tol=0.01)
    assert leaks == []


def test_loo_median_check_true_for_synthetic_market(synthetic_market_csv: Path):
    market = load_synthetic_market(synthetic_market_csv)
    _ = build_market_buckets(market)
    loo = leave_one_out_median(
        market, ["category", "material", "state"], "selling_price_inr"
    )
    assert loo.notna().sum() > 0


def test_cost_floor_not_a_feature_on_real_matrix(synthetic_market_csv: Path):
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    assert cost_floor_not_a_feature(X) is True
