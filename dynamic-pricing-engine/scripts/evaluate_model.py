from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DATA_DIR, PROCESSED_DIR, MODELS_DIR
from src.data.loaders import load_synthetic_market
from src.models.artifacts import load_artifacts
from src.models.preprocessing import build_feature_matrix, split_train_val_test, FEATURE_COLUMNS
from src.models.train import train_p50, train_quantile
from src.models.baselines import apply_cost_plus_baseline, apply_market_median_baseline
from src.models.evaluate import mae, rmse, mape, r2, pinball_loss


def _evaluate(y_true, y_pred):
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "r2": r2(y_true, y_pred),
    }


def main(out_path: Path | None = None) -> dict:
    market_path = PROCESSED_DIR / "market.parquet"
    if market_path.exists():
        market = pd.read_parquet(market_path)
    else:
        market = load_synthetic_market(DATA_DIR / "synthetic" / "dynamic_pricing_synthetic_market.csv")

    X = build_feature_matrix(market)
    y = market["selling_price_inr"].astype(float)
    Xtr, ytr, Xva, yva, Xte, yte = split_train_val_test(X, y, seed=42)

    artefacts_path = MODELS_DIR / "v1"
    if artefacts_path.exists() and (artefacts_path / "manifest.json").exists():
        artefacts = load_artifacts(artefacts_path)
        p50 = artefacts["p50"]
        p10 = artefacts["p10"]
        p50q = artefacts["p50_quantile"]
        p90 = artefacts["p90"]
    else:
        p50 = train_p50(Xtr, ytr)
        p10 = train_quantile(Xtr, ytr, alpha=0.10)
        p50q = train_quantile(Xtr, ytr, alpha=0.50)
        p90 = train_quantile(Xtr, ytr, alpha=0.90)

    pred_p50 = np.asarray(p50.predict(Xte), dtype=float)
    pred_p10 = np.asarray(p10.predict(Xte), dtype=float)
    pred_p50q = np.asarray(p50q.predict(Xte), dtype=float)
    pred_p90 = np.asarray(p90.predict(Xte), dtype=float)

    pred_cost_plus = apply_cost_plus_baseline(market.iloc[yte.index]) if False else None
    Xte_market = market.iloc[yte.index].reset_index(drop=True)
    pred_cost_plus = apply_cost_plus_baseline(Xte_market)
    pred_market_median = apply_market_median_baseline(Xte_market)

    yte_arr = yte.values

    result = {
        "cost_plus": _evaluate(yte_arr, pred_cost_plus),
        "market_median": _evaluate(yte_arr, pred_market_median),
        "lightgbm_p50": _evaluate(yte_arr, pred_p50),
        "lightgbm_p50_quantile": _evaluate(yte_arr, pred_p50q),
        "pinball": {
            "p10": pinball_loss(yte_arr, pred_p10, alpha=0.10),
            "p50": pinball_loss(yte_arr, pred_p50q, alpha=0.50),
            "p90": pinball_loss(yte_arr, pred_p90, alpha=0.90),
        },
        "n_test": int(len(yte_arr)),
    }

    if out_path is not None:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    out = main(out_path=Path("docs/eval_metrics.json"))
    print(json.dumps(out, indent=2, default=str))
