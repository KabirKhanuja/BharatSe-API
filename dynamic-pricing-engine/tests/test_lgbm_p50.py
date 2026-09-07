from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data.loaders import load_synthetic_market
from src.models.preprocessing import build_feature_matrix, split_train_val_test
from src.models.train import train_p50, train_quantile


def _matrix(synthetic_market_csv: Path):
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    y = market["selling_price_inr"].astype(float)
    return X, y


def test_train_p50_returns_predictor(synthetic_market_csv: Path):
    X, y = _matrix(synthetic_market_csv)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    model = train_p50(Xtr, ytr, params={"n_estimators": 50, "learning_rate": 0.1, "random_state": 42})
    preds = model.predict(Xte)
    assert np.isfinite(preds).all()
    assert (preds >= 0).all()


def test_train_p50_predictions_reproducible_with_seed(synthetic_market_csv: Path):
    X, y = _matrix(synthetic_market_csv)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    m1 = train_p50(Xtr, ytr, params={"n_estimators": 50, "random_state": 42})
    m2 = train_p50(Xtr, ytr, params={"n_estimators": 50, "random_state": 42})
    p1 = m1.predict(Xte)
    p2 = m2.predict(Xte)
    np.testing.assert_array_equal(p1, p2)


def test_train_p50_r2_above_sanity_threshold(synthetic_market_csv: Path):
    X, y = _matrix(synthetic_market_csv)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    model = train_p50(Xtr, ytr, params={"n_estimators": 200, "learning_rate": 0.05, "random_state": 42})
    preds = model.predict(Xte)
    ss_res = float(np.sum((yte.values - preds) ** 2))
    ss_tot = float(np.sum((yte.values - yte.values.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    assert r2 > 0.5, f"R² too low: {r2}"


def test_train_quantile_returns_predictor(synthetic_market_csv: Path):
    X, y = _matrix(synthetic_market_csv)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    model = train_quantile(Xtr, ytr, alpha=0.5, params={"n_estimators": 50, "random_state": 42})
    preds = model.predict(Xte)
    assert np.isfinite(preds).all()


def test_train_p50_respects_n_estimators(synthetic_market_csv: Path):
    X, y = _matrix(synthetic_market_csv)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)
    small = train_p50(Xtr, ytr, params={"n_estimators": 10, "random_state": 42})
    big = train_p50(Xtr, ytr, params={"n_estimators": 200, "random_state": 42})
    assert hasattr(small, "predict")
    assert hasattr(big, "predict")
    assert small.predict(Xte).shape == big.predict(Xte).shape
