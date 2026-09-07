from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd
import pytest

from src.data.loaders import load_synthetic_market
from src.features.market_features import build_market_buckets
from src.models.preprocessing import build_feature_matrix, split_train_val_test
from src.models.train import train_p50, train_quantile
from src.models.evaluate import enforce_quantile_order
from src.models.inference import predict_price


def _artifacts(synthetic_market_csv: Path):
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    y = market["selling_price_inr"].astype(float)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    p50 = train_p50(Xtr, ytr, params={"n_estimators": 100, "random_state": 42})
    p10 = train_quantile(Xtr, ytr, alpha=0.10, params={"n_estimators": 100, "random_state": 42})
    p50q = train_quantile(Xtr, ytr, alpha=0.50, params={"n_estimators": 100, "random_state": 42})
    p90 = train_quantile(Xtr, ytr, alpha=0.90, params={"n_estimators": 100, "random_state": 42})
    buckets = build_market_buckets(market)
    categorical_levels = {
        c: list(Xtr[c].cat.categories) for c in Xtr.columns if str(Xtr[c].dtype) == "category"
    }
    return {
        "p50": p50,
        "p10": p10,
        "p50_quantile": p50q,
        "p90": p90,
        "market_buckets": buckets,
        "categorical_levels": categorical_levels,
    }


def test_predict_price_returns_required_keys(synthetic_market_csv: Path):
    arts = _artifacts(synthetic_market_csv)
    request = {
        "category": "Saree",
        "craft_type": "Handloom",
        "material": "Silk",
        "state": "Maharashtra",
        "district": "Pune",
        "size_m_or_units": 5.5,
        "weight_kg": 1.2,
        "handmade": True,
        "quality_grade": 4,
        "design_complexity": 3,
        "raw_material_cost_inr": 800.0,
        "labour_cost_inr": 1200.0,
        "inbound_procurement_cost_inr": 200.0,
        "production_overhead_inr": 300.0,
        "season": "Wedding",
    }
    out = predict_price(request, arts)
    for k in ("p10", "p50", "p90", "recommended_price"):
        assert k in out


def test_predict_price_quantile_ordering_holds(synthetic_market_csv: Path):
    arts = _artifacts(synthetic_market_csv)
    request = {
        "category": "Saree",
        "craft_type": "Handloom",
        "material": "Silk",
        "state": "Maharashtra",
        "district": "Pune",
        "size_m_or_units": 5.5,
        "weight_kg": 1.2,
        "handmade": True,
        "quality_grade": 4,
        "design_complexity": 3,
        "raw_material_cost_inr": 800.0,
        "labour_cost_inr": 1200.0,
        "inbound_procurement_cost_inr": 200.0,
        "production_overhead_inr": 300.0,
        "season": "Wedding",
    }
    out = predict_price(request, arts)
    assert out["p10"] <= out["p50"] <= out["p90"]


def test_predict_price_values_are_positive_and_finite(synthetic_market_csv: Path):
    arts = _artifacts(synthetic_market_csv)
    request = {
        "category": "Bag",
        "craft_type": "Basketry",
        "material": "Jute",
        "state": "Gujarat",
        "district": "Surat",
        "size_m_or_units": 3.0,
        "weight_kg": 0.5,
        "handmade": True,
        "quality_grade": 3,
        "design_complexity": 2,
        "raw_material_cost_inr": 300.0,
        "labour_cost_inr": 400.0,
        "inbound_procurement_cost_inr": 100.0,
        "production_overhead_inr": 150.0,
        "season": "Normal",
    }
    out = predict_price(request, arts)
    for k in ("p10", "p50", "p90", "recommended_price"):
        v = out[k]
        assert v > 0
        assert math.isfinite(v)
