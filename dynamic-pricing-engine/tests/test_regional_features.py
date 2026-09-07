from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.loaders import load_odop, load_synthetic_market
from src.features.regional_features import build_state_aggregates, UnknownRegionError


@pytest.fixture(scope="module")
def odop_df(odop_csv: Path) -> pd.DataFrame:
    return load_odop(odop_csv)


@pytest.fixture(scope="module")
def state_aggs(odop_df: pd.DataFrame) -> pd.DataFrame:
    return build_state_aggregates(odop_df)


REQUIRED_STATE_COLS = {
    "odop_state_product_count", "odop_state_gi_count", "odop_state_sector_count",
}


def test_state_aggregates_have_one_row_per_state(state_aggs: pd.DataFrame, odop_df: pd.DataFrame):
    assert len(state_aggs) == odop_df["State"].nunique()
    assert REQUIRED_STATE_COLS.issubset(set(state_aggs.columns))


def test_state_product_count_matches_groupby(state_aggs: pd.DataFrame, odop_df: pd.DataFrame):
    expected = odop_df.groupby("State").size().rename("odop_state_product_count")
    merged = state_aggs.join(expected, how="inner", rsuffix="_expected")
    assert (merged["odop_state_product_count"] == merged["odop_state_product_count_expected"]).all()


def test_gi_count_within_bounds(state_aggs: pd.DataFrame):
    assert (state_aggs["odop_state_gi_count"] >= 0).all()
    assert (state_aggs["odop_state_gi_count"] <= state_aggs["odop_state_product_count"]).all()


def test_state_join_is_left_and_does_not_duplicate(synthetic_market_csv: Path, state_aggs: pd.DataFrame):
    market = load_synthetic_market(synthetic_market_csv)
    out = market.merge(state_aggs, left_on="state", right_index=True, how="left")
    assert len(out) == len(market)
    for col in REQUIRED_STATE_COLS:
        assert col in out.columns
