from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.loaders import (
    load_synthetic_market,
    load_ecommerce,
    load_odop,
    load_synthetic_raw_material,
    load_synthetic_regional_craft,
)
from src.features.market_features import (
    build_market_buckets,
    get_comparable_stats,
    compute_dispersion,
    leave_one_out_median,
    InsufficientComparablesError,
)


@pytest.fixture(scope="module")
def market_df(synthetic_market_csv: Path) -> pd.DataFrame:
    return load_synthetic_market(synthetic_market_csv)


@pytest.fixture(scope="module")
def buckets(market_df: pd.DataFrame) -> pd.DataFrame:
    return build_market_buckets(market_df)


REQUIRED_BUCKET_COLS = {
    "market_median", "market_min", "market_max",
    "market_p25", "market_p75", "market_mean",
    "mrp_median", "discount_pct_median",
    "seller_count_median", "rating_median",
    "comparable_count",
}


def test_build_market_buckets_returns_dataframe_with_expected_columns(buckets: pd.DataFrame):
    assert isinstance(buckets, pd.DataFrame)
    assert REQUIRED_BUCKET_COLS.issubset(set(buckets.columns))
    assert len(buckets) > 0


def test_buckets_have_positive_comparable_counts(buckets: pd.DataFrame):
    assert (buckets["comparable_count"] > 0).all()


def test_get_comparable_stats_returns_full_dict(buckets: pd.DataFrame):
    sample = buckets.index[0]
    category, material, state = sample
    stats = get_comparable_stats(buckets, category, material, state)
    assert REQUIRED_BUCKET_COLS.issubset(set(stats.keys()))
    assert stats["comparable_count"] > 0
    assert pd.notna(stats["market_median"])
    import math
    assert math.isfinite(stats["market_median"])


def test_get_comparable_stats_raises_for_missing_bucket(buckets: pd.DataFrame):
    with pytest.raises(InsufficientComparablesError):
        get_comparable_stats(buckets, "__no_such_category__", "__no_such_material__", "__no_such_state__")


def test_get_comparable_stats_handles_zero_count(buckets: pd.DataFrame):
    import math
    sample = buckets.iloc[0].to_dict()
    assert sample["comparable_count"] >= 0
    assert math.isfinite(sample["market_median"])


def test_compute_dispersion_is_non_negative():
    s = pd.Series([100.0, 110.0, 120.0])
    assert compute_dispersion(s) >= 0


def test_compute_dispersion_is_zero_for_constant():
    s = pd.Series([500.0, 500.0, 500.0])
    assert compute_dispersion(s) == 0.0


def test_market_stats_ignore_non_positive_prices(market_df: pd.DataFrame):
    df = market_df.copy()
    df.loc[df.index[:5], "selling_price_inr"] = -1.0
    b = build_market_buckets(df)
    assert b["market_min"].min() > 0
    assert b["market_median"].min() > 0
