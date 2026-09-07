from __future__ import annotations
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, PROCESSED_DIR, MODELS_DIR
from src.data.loaders import load_synthetic_market
from src.features.market_features import build_market_buckets
from src.models.preprocessing import build_feature_matrix, split_train_val_test, FEATURE_COLUMNS
from src.models.train import train_p50, train_quantile
from src.models.artifacts import save_artifacts


def main() -> Path:
    out_dir = MODELS_DIR / "v1"
    out_dir.mkdir(parents=True, exist_ok=True)

    market_path = PROCESSED_DIR / "market.parquet"
    if market_path.exists():
        market = pd.read_parquet(market_path)
    else:
        market = load_synthetic_market(DATA_DIR / "synthetic" / "dynamic_pricing_synthetic_market.csv")

    buckets_path = PROCESSED_DIR / "market_buckets.parquet"
    if buckets_path.exists():
        market_buckets = pd.read_parquet(buckets_path)
    else:
        market_buckets = build_market_buckets(market)

    X = build_feature_matrix(market)
    y = market["selling_price_inr"].astype(float)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)

    p50 = train_p50(Xtr, ytr)
    p10 = train_quantile(Xtr, ytr, alpha=0.10)
    p50q = train_quantile(Xtr, ytr, alpha=0.50)
    p90 = train_quantile(Xtr, ytr, alpha=0.90)

    models = {"p50": p50, "p10": p10, "p50_quantile": p50q, "p90": p90}
    categorical_levels = {c: list(Xtr[c].cat.categories) for c in Xtr.columns if str(Xtr[c].dtype) == "category"}
    imputation = {}
    save_artifacts(models, FEATURE_COLUMNS, categorical_levels, imputation, out_dir,
                  market_buckets=market_buckets)
    return out_dir


if __name__ == "__main__":
    print(main())
