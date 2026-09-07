from __future__ import annotations
from pathlib import Path
import math
import pandas as pd
import pytest

from src.data.loaders import load_synthetic_raw_material
from src.features.material_features import (
    build_material_trend,
    lookup_material_trend,
    UnknownMaterialError,
)


@pytest.fixture(scope="module")
def raw_df(synthetic_raw_material_csv: Path) -> pd.DataFrame:
    return load_synthetic_raw_material(synthetic_raw_material_csv)


@pytest.fixture(scope="module")
def trend(raw_df: pd.DataFrame) -> pd.DataFrame:
    return build_material_trend(raw_df)


REQUIRED_TREND_COLS = {"material_price_latest", "material_trend_30d_pct", "material_price_latest_date"}


def test_material_trend_has_one_row_per_state_material(trend: pd.DataFrame, raw_df: pd.DataFrame):
    expected = raw_df[["state", "material"]].drop_duplicates().shape[0]
    assert len(trend) == expected
    assert REQUIRED_TREND_COLS.issubset(set(trend.columns))


def test_material_price_latest_positive_and_finite(trend: pd.DataFrame):
    assert (trend["material_price_latest"] > 0).all()
    assert trend["material_price_latest"].notna().all()


def test_trend_30d_pct_finite(trend: pd.DataFrame):
    s = trend["material_trend_30d_pct"].dropna()
    assert all(math.isfinite(v) for v in s)


def test_lookup_returns_dict_for_known(trend: pd.DataFrame):
    sample = trend.index[0]
    state, material = sample
    out = lookup_material_trend(trend, state, material)
    assert REQUIRED_TREND_COLS.issubset(set(out.keys()))
    assert out["material_price_latest"] > 0


def test_lookup_for_unknown_raises_or_returns_sentinel(trend: pd.DataFrame):
    raised = False
    try:
        lookup_material_trend(trend, "__no_state__", "__no_material__")
    except UnknownMaterialError:
        raised = True
    if not raised:
        out = lookup_material_trend(trend, "__no_state__", "__no_material__")
        assert pd.isna(out["material_price_latest"])
