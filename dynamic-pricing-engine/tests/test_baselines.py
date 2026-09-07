from __future__ import annotations
import math
import numpy as np
import pandas as pd
import pytest

from src.models.baselines import (
    cost_plus_baseline,
    market_median_baseline,
    category_median_margin,
    apply_cost_plus_baseline,
    apply_market_median_baseline,
    BaselineValidationError,
)


def test_cost_plus_baseline_multiplies():
    assert cost_plus_baseline(2000.0, margin=1.5) == 3000.0
    assert cost_plus_baseline(2000.0, margin=1.0) == 2000.0


def test_cost_plus_baseline_rejects_margin_below_one():
    with pytest.raises(BaselineValidationError):
        cost_plus_baseline(2000.0, margin=0.9)


def test_market_median_baseline_passes_through():
    assert market_median_baseline(2500.0) == 2500.0
    assert market_median_baseline(None) is None


def test_category_median_margin_known_value():
    df = pd.DataFrame({
        "category": ["Saree", "Saree", "Bag"],
        "selling_price_inr": [3000.0, 3000.0, 1000.0],
        "cost_floor_inr": [2500.0, 2500.0, 1000.0],
    })
    margins = category_median_margin(df)
    assert margins["Saree"] == pytest.approx(1.2, rel=1e-3)
    assert margins["Bag"] == pytest.approx(1.0, rel=1e-3)


def test_apply_cost_plus_baseline_no_nan_no_zero(synthetic_market_csv):
    from src.data.loaders import load_synthetic_market
    market = load_synthetic_market(synthetic_market_csv)
    preds = apply_cost_plus_baseline(market)
    assert isinstance(preds, np.ndarray)
    assert not np.isnan(preds).any()
    assert (preds > 0).all()


def test_apply_market_median_baseline_no_nan(synthetic_market_csv):
    from src.data.loaders import load_synthetic_market
    market = load_synthetic_market(synthetic_market_csv)
    preds = apply_market_median_baseline(market)
    assert not np.isnan(preds).any()
    assert (preds > 0).all()
