"""LightGBM quantile regression for price bands.

Three separate models, one per quantile. LightGBM is used rather than XGBoost
because it has a native quantile objective, so the band comes straight out of
the model instead of being bolted on afterwards, and it is faster on small
tabular data.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger
from app.services.pricing.features import CATEGORICAL, FEATURE_ORDER, PriceInput, to_frame

log = get_logger(__name__)

QUANTILES = (0.1, 0.5, 0.9)
MODEL_FILENAMES = {q: f"price_q{int(q * 100)}.txt" for q in QUANTILES}
METADATA_FILENAME = "price_meta.json"


def train_quantile_models(
    frame: pd.DataFrame,
    target: pd.Series,
    num_boost_round: int = 400,
) -> dict[float, object]:
    """Fit one booster per quantile.

    `alpha` must be passed explicitly. It defaults to 0.9, so omitting it
    silently trains three identical P90 models and the band collapses.
    """
    import lightgbm as lgb

    dataset = lgb.Dataset(frame, label=target, categorical_feature=CATEGORICAL)
    boosters: dict[float, object] = {}

    for q in QUANTILES:
        params = {
            "objective": "quantile",
            "alpha": q,
            "metric": "quantile",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 20,
            "feature_fraction": 0.9,
            "verbosity": -1,
        }
        boosters[q] = lgb.train(params, dataset, num_boost_round=num_boost_round)
        log.info("trained_quantile_model", quantile=q)

    return boosters


def save_models(boosters: dict[float, object], directory: str | None = None) -> Path:
    out = Path(directory or settings.PRICE_MODEL_DIR)
    out.mkdir(parents=True, exist_ok=True)

    for q, booster in boosters.items():
        booster.save_model(str(out / MODEL_FILENAMES[q]))  # type: ignore[attr-defined]

    (out / METADATA_FILENAME).write_text(
        json.dumps({"quantiles": list(QUANTILES), "features": FEATURE_ORDER}, indent=2)
    )
    return out


class PriceBandModel:
    """Loads the three boosters once and predicts a band."""

    def __init__(self, directory: str | None = None) -> None:
        self.directory = Path(directory or settings.PRICE_MODEL_DIR)
        self._boosters: dict[float, object] | None = None

    @property
    def is_trained(self) -> bool:
        return all((self.directory / f).exists() for f in MODEL_FILENAMES.values())

    def load(self) -> None:
        import lightgbm as lgb

        if not self.is_trained:
            raise FileNotFoundError(
                f"No trained price model in {self.directory}. "
                "Run: python -m app.services.pricing.train"
            )

        self._boosters = {
            q: lgb.Booster(model_file=str(self.directory / name))
            for q, name in MODEL_FILENAMES.items()
        }
        log.info("price_model_loaded", directory=str(self.directory))

    def predict(self, items: list[PriceInput]) -> np.ndarray:
        """Return an (n, 3) array of P10, P50, P90 in rupees."""
        if self._boosters is None:
            self.load()
        assert self._boosters is not None

        frame = to_frame(items)
        raw = np.vstack([self._boosters[q].predict(frame) for q in QUANTILES])  # type: ignore[attr-defined]

        # Quantiles are fit independently, so nothing stops P10 landing above
        # P90 on an individual row. Sorting each column fixes it and costs
        # nothing. A P10 above a P90 on stage would destroy the demo.
        raw = np.sort(raw, axis=0)
        return raw.T


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
    """The metric to quote for a quantile model, not RMSE."""
    delta = y_true - y_pred
    return float(np.mean(np.maximum(quantile * delta, (quantile - 1) * delta)))


def empirical_coverage(y_true: np.ndarray, low: np.ndarray, high: np.ndarray) -> float:
    """Share of true prices that landed inside the band.

    This is the answer to "are your intervals calibrated". For a P10 to P90
    band it should sit near 0.80.
    """
    return float(np.mean((y_true >= low) & (y_true <= high)))
