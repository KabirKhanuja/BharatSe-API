from __future__ import annotations
from typing import Any, Optional
import numpy as np
import pandas as pd


def _default_p50_params() -> dict:
    return {
        "n_estimators": 400,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 20,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
        "objective": "regression_l1",
        "random_state": 42,
        "verbose": -1,
    }


def _default_quantile_params() -> dict:
    return {
        "n_estimators": 400,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 20,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
        "random_state": 42,
        "verbose": -1,
    }


def train_p50(X: pd.DataFrame, y: pd.Series, params: Optional[dict] = None) -> Any:
    import lightgbm as lgb
    p = _default_p50_params()
    if params:
        p.update(params)
    model = lgb.LGBMRegressor(**p)
    model.fit(X, y)
    return model


def train_quantile(X: pd.DataFrame, y: pd.Series, alpha: float, params: Optional[dict] = None) -> Any:
    import lightgbm as lgb
    p = _default_quantile_params()
    p["objective"] = "quantile"
    p["alpha"] = float(alpha)
    if params:
        p.update(params)
    model = lgb.LGBMRegressor(**p)
    model.fit(X, y)
    return model
