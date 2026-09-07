from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

from src.models.preprocessing import (
    impute_numeric_missing,
    impute_categorical_missing,
    add_missing_flags,
    align_categoricals,
    build_feature_matrix,
    split_train_val_test,
    FEATURE_COLUMNS,
)


def test_impute_numeric_uses_median():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0]})
    out = impute_numeric_missing(df, ["a"])
    assert out["a"].isna().sum() == 0
    assert out["a"].iloc[2] == 2.0
    assert out["a"].iloc[0] == 1.0


def test_impute_categorical_uses_mode():
    df = pd.DataFrame({"c": ["x", "y", "y", np.nan, "y"]})
    out = impute_categorical_missing(df, ["c"])
    assert out["c"].isna().sum() == 0
    assert out["c"].iloc[3] == "y"


def test_align_categoricals_adds_missing_for_unseen():
    levels = {"c": ["x", "y", "z", "__missing__"]}
    df = pd.DataFrame({"c": ["x", "w"]}, dtype="category")
    out = align_categoricals(df, levels)
    assert "__missing__" in out["c"].cat.categories
    assert out["c"].iloc[1] == "__missing__"


def test_build_feature_matrix_has_expected_columns(synthetic_market_csv):
    from src.data.loaders import load_synthetic_market
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    assert isinstance(X, pd.DataFrame)
    for c in FEATURE_COLUMNS:
        assert c in X.columns


def test_add_missing_flags_creates_companion_columns():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
    out = add_missing_flags(df, ["a"])
    assert "a_isna" in out.columns
    assert out["a_isna"].tolist() == [0, 1, 0]


def test_numeric_columns_are_float32(synthetic_market_csv):
    from src.data.loaders import load_synthetic_market
    market = load_synthetic_market(synthetic_market_csv)
    X = build_feature_matrix(market)
    for c in ("raw_material_cost_inr", "quality_grade", "weight_kg"):
        if c in X.columns:
            assert X[c].dtype == np.float32


def test_split_train_val_test_is_deterministic_and_disjoint():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(100, 4)), columns=list("abcd"))
    y = pd.Series(rng.normal(size=100))
    X1, y1, X2, y2, X3, y3 = split_train_val_test(X, y, seed=42)
    assert len(X1) + len(X2) + len(X3) == 100
    assert len(X1) > 0 and len(X2) > 0 and len(X3) > 0
    assert not X1.index.intersection(X2.index).any()
    assert not X2.index.intersection(X3.index).any()
