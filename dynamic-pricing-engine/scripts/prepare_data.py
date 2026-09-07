from __future__ import annotations
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, PROCESSED_DIR
from src.data.loaders import (
    load_synthetic_market,
    load_ecommerce,
    load_odop,
    load_synthetic_raw_material,
)
from src.data.validators import (
    validate_synthetic_market,
    validate_ecommerce,
    validate_odop,
    validate_raw_material,
)
from src.features.market_features import build_market_buckets
from src.features.demand_features import build_category_aggregates
from src.features.regional_features import build_state_aggregates
from src.features.material_features import build_material_trend
from src.models.preprocessing import build_feature_matrix


def main() -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    market = load_synthetic_market(DATA_DIR / "synthetic" / "dynamic_pricing_synthetic_market.csv")
    validate_synthetic_market(market)
    ecommerce = load_ecommerce(DATA_DIR / "ecommerce_customer_behavior" / "Ecommerce.csv")
    validate_ecommerce(ecommerce)
    odop = load_odop(DATA_DIR / "odop" / "20250707_ODOP_Products_V31.csv")
    validate_odop(odop)
    raw_material = load_synthetic_raw_material(DATA_DIR / "synthetic" / "dynamic_pricing_synthetic_raw_material.csv")
    validate_raw_material(raw_material)

    market_buckets = build_market_buckets(market)
    category_aggregates = build_category_aggregates(ecommerce)
    state_aggregates = build_state_aggregates(odop)
    material_trend = build_material_trend(raw_material)

    market.to_parquet(PROCESSED_DIR / "market.parquet", index=False)
    market_buckets.to_parquet(PROCESSED_DIR / "market_buckets.parquet")
    category_aggregates.to_parquet(PROCESSED_DIR / "category_aggregates.parquet")
    state_aggregates.to_parquet(PROCESSED_DIR / "state_aggregates.parquet")
    material_trend.to_parquet(PROCESSED_DIR / "material_trend.parquet")

    feature_cols = list(build_feature_matrix(market).columns)
    (PROCESSED_DIR / "feature_columns.json").write_text(
        __import__("json").dumps(feature_cols)
    )
    return PROCESSED_DIR


if __name__ == "__main__":
    print(main())
