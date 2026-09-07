from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass
class DataQualityReport:
    rows: int
    columns: list
    null_counts: dict
    duplicate_count: int


class SchemaValidationError(ValueError):
    pass


REQUIRED_SYNTHETIC_MARKET_COLS = [
    "product_id", "category", "craft_type", "material", "state", "district",
    "size_m_or_units", "weight_kg", "handmade", "quality_grade", "design_complexity",
    "raw_material_cost_inr", "labour_cost_inr", "inbound_procurement_cost_inr",
    "production_overhead_inr", "cost_floor_inr", "selling_price_inr", "mrp_inr",
    "discount_pct", "seller_count", "rating", "review_count", "stock_units",
    "trend_7d_pct", "trend_30d_pct", "trend_90d_pct", "season", "demand_index",
]

REQUIRED_ECOMMERCE_COLS = [
    "customer_id", "session_id", "visit_date", "device_type", "user_type",
    "marketing_channel", "product_id", "product_category", "unit_price", "quantity",
    "discount_percent", "discount_amount", "revenue", "pages_viewed", "time_on_site_sec",
    "added_to_cart", "purchased", "cart_abandoned", "rating", "review_text",
    "review_helpful_votes", "payment_method", "visit_day", "visit_month", "visit_weekday",
    "visit_season", "session_duration_bucket", "revenue_normalized", "location",
]

REQUIRED_ODOP_COLS = [
    "State", "Product", "District", "LGD Code", "Category", "Sector",
    "Description", "GI Status", "Photo", "Ministry/ Department",
]

REQUIRED_FASHION_COLS = [
    "image_url", "image_path", "brand", "product_title", "class_label", "color",
]

REQUIRED_RAW_MATERIAL_COLS = [
    "state", "district_or_market", "material", "date", "modal_price_inr_per_unit",
]


def _report(df: pd.DataFrame) -> DataQualityReport:
    return DataQualityReport(
        rows=len(df),
        columns=list(df.columns),
        null_counts={c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        duplicate_count=int(df.duplicated().sum()),
    )


def _require_columns(df: pd.DataFrame, required: list, source: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SchemaValidationError(
            f"{source}: missing required columns: {missing}"
        )


def _require_non_null(df: pd.DataFrame, cols: list, source: str) -> None:
    for c in cols:
        if c in df.columns and df[c].isna().any():
            raise SchemaValidationError(
                f"{source}: column '{c}' contains nulls"
            )


def validate_synthetic_market(df: pd.DataFrame) -> DataQualityReport:
    _require_columns(df, REQUIRED_SYNTHETIC_MARKET_COLS, "synthetic_market")

    if (df["selling_price_inr"] < 0).any():
        raise SchemaValidationError("synthetic_market: negative selling_price_inr")

    computed_floor = (
        df["raw_material_cost_inr"]
        + df["labour_cost_inr"]
        + df["inbound_procurement_cost_inr"]
        + df["production_overhead_inr"]
    )
    diff = (df["cost_floor_inr"] - computed_floor).abs()
    if (diff > 0.01).any():
        bad = df.loc[diff > 0.01].head(3)
        raise SchemaValidationError(
            f"synthetic_market: cost_floor inconsistent with components; sample={bad.index.tolist()}"
        )

    if df["product_id"].duplicated().any():
        raise SchemaValidationError("synthetic_market: duplicate product_id")

    return _report(df)


def validate_ecommerce(df: pd.DataFrame) -> DataQualityReport:
    _require_columns(df, REQUIRED_ECOMMERCE_COLS, "ecommerce")
    _require_non_null(df, REQUIRED_ECOMMERCE_COLS, "ecommerce")
    return _report(df)


def validate_odop(df: pd.DataFrame) -> DataQualityReport:
    _require_columns(df, REQUIRED_ODOP_COLS, "odop")
    _require_non_null(df, ["State", "Product", "District", "LGD Code", "Category"], "odop")
    return _report(df)


def validate_fashion(df: pd.DataFrame) -> DataQualityReport:
    _require_columns(df, REQUIRED_FASHION_COLS, "fashion")
    return _report(df)


def validate_raw_material(df: pd.DataFrame) -> DataQualityReport:
    _require_columns(df, REQUIRED_RAW_MATERIAL_COLS, "raw_material")
    if (df["modal_price_inr_per_unit"] <= 0).any():
        raise SchemaValidationError("raw_material: non-positive modal_price_inr_per_unit")
    return _report(df)
