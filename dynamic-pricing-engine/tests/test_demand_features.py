from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.loaders import load_ecommerce
from src.features.demand_features import (
    build_category_aggregates,
    build_category_month_aggregates,
    category_id_to_label,
)


@pytest.fixture(scope="module")
def ecommerce_df(ecommerce_csv: Path) -> pd.DataFrame:
    return load_ecommerce(ecommerce_csv)


@pytest.fixture(scope="module")
def cat_aggs(ecommerce_df: pd.DataFrame) -> pd.DataFrame:
    return build_category_aggregates(ecommerce_df)


@pytest.fixture(scope="module")
def cat_month_aggs(ecommerce_df: pd.DataFrame) -> pd.DataFrame:
    return build_category_month_aggregates(ecommerce_df)


REQUIRED_CAT_COLS = {
    "ec_purchase_rate", "ec_avg_unit_price", "ec_avg_discount",
    "ec_avg_rating", "ec_visit_count", "ec_price_volatility",
}


def test_category_aggregates_have_one_row_per_category(cat_aggs: pd.DataFrame, ecommerce_df: pd.DataFrame):
    assert len(cat_aggs) == ecommerce_df["product_category"].nunique()
    assert REQUIRED_CAT_COLS.issubset(set(cat_aggs.columns))


def test_purchase_rate_in_unit_interval(cat_aggs: pd.DataFrame):
    assert (cat_aggs["ec_purchase_rate"] >= 0).all()
    assert (cat_aggs["ec_purchase_rate"] <= 1).all()


def test_avg_unit_price_positive_and_finite(cat_aggs: pd.DataFrame):
    assert (cat_aggs["ec_avg_unit_price"] > 0).all()
    assert cat_aggs["ec_avg_unit_price"].notna().all()


def test_category_month_aggregates_cardinality(cat_month_aggs: pd.DataFrame, ecommerce_df: pd.DataFrame):
    expected = ecommerce_df["product_category"].nunique() * ecommerce_df["visit_month"].nunique()
    assert len(cat_month_aggs) == expected


def test_category_id_to_label_returns_mapping(ecommerce_df: pd.DataFrame):
    m = category_id_to_label(ecommerce_df)
    assert isinstance(m, dict)
    assert len(m) == ecommerce_df["product_category"].nunique()
    assert all(isinstance(v, str) for v in m.values())


def test_price_volatility_non_negative(cat_aggs: pd.DataFrame):
    assert (cat_aggs["ec_price_volatility"] >= 0).all()
