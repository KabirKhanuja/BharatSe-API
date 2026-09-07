from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.loaders import (
    load_indian_fashion,
    load_ecommerce,
    load_odop,
    load_synthetic_market,
    load_synthetic_raw_material,
    load_synthetic_regional_craft,
)
from src.data.validators import SchemaValidationError


FASHION_COLS = {"image_url", "image_path", "brand", "product_title", "class_label", "color"}
ODOP_COLS = {
    "State", "Product", "District", "LGD Code", "Category", "Sector",
    "Description", "GI Status", "Photo", "Ministry/ Department",
}


def test_load_indian_fashion_returns_dataframe_with_expected_columns(fashion_dir: Path):
    df = load_indian_fashion(fashion_dir)
    assert isinstance(df, pd.DataFrame)
    assert FASHION_COLS.issubset(set(df.columns))
    assert len(df) > 100_000, f"expected >100k rows, got {len(df)}"


def test_load_ecommerce_returns_25k_rows_with_29_cols(ecommerce_csv: Path):
    df = load_ecommerce(ecommerce_csv)
    assert len(df) == 25_000
    assert len(df.columns) == 29
    assert df.isna().sum().sum() == 0


def test_load_odop_handles_latin1_encoding(odop_csv: Path):
    df = load_odop(odop_csv)
    assert len(df) == 1_241
    assert ODOP_COLS.issubset(set(df.columns))
    assert "Andaman" in str(df["State"].iloc[0])


def test_load_synthetic_market_returns_6k_rows_28_cols(synthetic_market_csv: Path):
    df = load_synthetic_market(synthetic_market_csv)
    assert len(df) == 6_000
    assert len(df.columns) == 28
    assert "selling_price_inr" in df.columns
    assert "cost_floor_inr" in df.columns


def test_load_synthetic_raw_material_returns_900_rows(synthetic_raw_material_csv: Path):
    df = load_synthetic_raw_material(synthetic_raw_material_csv)
    assert len(df) == 900
    assert "modal_price_inr_per_unit" in df.columns
    assert pd.api.types.is_numeric_dtype(df["modal_price_inr_per_unit"])


def test_load_synthetic_regional_craft_returns_120_rows(synthetic_regional_craft_csv: Path):
    df = load_synthetic_regional_craft(synthetic_regional_craft_csv)
    assert len(df) == 120
    assert {"state", "district", "craft_type", "typical_material", "typical_category"}.issubset(df.columns)


def test_loader_raises_on_missing_file(tmp_path: Path):
    from src.data.loaders import DataSourceError
    with pytest.raises((FileNotFoundError, DataSourceError)):
        load_ecommerce(tmp_path / "does_not_exist.csv")


def test_loader_is_idempotent(synthetic_market_csv: Path):
    a = load_synthetic_market(synthetic_market_csv)
    b = load_synthetic_market(synthetic_market_csv)
    assert len(a) == len(b)
    assert set(a.columns) == set(b.columns)
