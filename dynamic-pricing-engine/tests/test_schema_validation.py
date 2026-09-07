from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.validators import (
    validate_synthetic_market,
    validate_ecommerce,
    validate_odop,
    validate_fashion,
    validate_raw_material,
    SchemaValidationError,
)


REQUIRED_SYNTHETIC_MARKET_COLS = [
    "product_id", "category", "craft_type", "material", "state", "district",
    "size_m_or_units", "weight_kg", "handmade", "quality_grade", "design_complexity",
    "raw_material_cost_inr", "labour_cost_inr", "inbound_procurement_cost_inr",
    "production_overhead_inr", "cost_floor_inr", "selling_price_inr", "mrp_inr",
    "discount_pct", "seller_count", "rating", "review_count", "stock_units",
    "trend_7d_pct", "trend_30d_pct", "trend_90d_pct", "season", "demand_index",
]


def test_validate_synthetic_market_required_columns_present(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv)
    report = validate_synthetic_market(df)
    assert report.rows == len(df)
    assert set(report.columns) == set(REQUIRED_SYNTHETIC_MARKET_COLS)


def test_validate_synthetic_market_missing_target_raises(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv).drop(columns=["selling_price_inr"])
    with pytest.raises(SchemaValidationError):
        validate_synthetic_market(df)


def test_validate_synthetic_market_negative_price_raises(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv)
    df.loc[0, "selling_price_inr"] = -1.0
    with pytest.raises(SchemaValidationError):
        validate_synthetic_market(df)


def test_validate_synthetic_market_cost_floor_consistency(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv)
    report = validate_synthetic_market(df)
    assert report.rows == len(df)


def test_validate_synthetic_market_cost_floor_inconsistency_raises(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv).copy()
    df.loc[0, "cost_floor_inr"] = df.loc[0, "cost_floor_inr"] + 1000.0
    with pytest.raises(SchemaValidationError):
        validate_synthetic_market(df)


def test_validate_ecommerce_columns_and_types(ecommerce_csv: Path):
    df = pd.read_csv(ecommerce_csv)
    report = validate_ecommerce(df)
    assert report.rows == 25_000
    assert report.null_counts == {}


def test_validate_odop_columns_and_no_nulls_in_keys(odop_csv: Path):
    df = pd.read_csv(odop_csv, encoding="latin-1")
    report = validate_odop(df)
    assert report.rows == 1_241
    for key in ["State", "Product", "District", "LGD Code", "Category"]:
        assert report.null_counts.get(key, 0) == 0


def test_validate_fashion_columns(fashion_dir: Path):
    df = pd.concat(
        [pd.read_csv(p) for p in sorted(fashion_dir.glob("*.csv"))],
        ignore_index=True,
    )
    report = validate_fashion(df)
    assert report.rows == len(df)
    for col in ["class_label", "product_title", "image_url", "image_path", "brand", "color"]:
        assert col in report.columns


def test_validate_raw_material_modal_price_positive(synthetic_raw_material_csv: Path):
    df = pd.read_csv(synthetic_raw_material_csv)
    report = validate_raw_material(df)
    assert report.rows == 900
    assert (df["modal_price_inr_per_unit"] > 0).all()


def test_validate_returns_clean_frame_with_no_duplicate_ids(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv)
    report = validate_synthetic_market(df)
    assert report.duplicate_count == 0


def test_validate_produces_quality_report(synthetic_market_csv: Path):
    df = pd.read_csv(synthetic_market_csv)
    report = validate_synthetic_market(df)
    assert hasattr(report, "rows")
    assert hasattr(report, "columns")
    assert hasattr(report, "null_counts")
    assert hasattr(report, "duplicate_count")
