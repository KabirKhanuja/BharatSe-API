"""Train the price band models.

    python -m app.services.pricing.train --csv data/seed/flipkart.csv

The seed data is a public Flipkart product dump, crawled in 2016. Prices are a
decade stale, and we say so rather than hiding it: the model is used for
STRUCTURE, meaning how material, category and size move price relative to each
other, not for absolute rupee truth. A small hand built current price table is
layered on top for the crafts we actually pitch.

Source: PromptCloud, Flipkart Products, CC BY SA 4.0.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.logging import configure_logging, get_logger
from app.services.pricing.features import PriceInput, to_frame
from app.services.pricing.model import (
    QUANTILES,
    empirical_coverage,
    pinball_loss,
    save_models,
    train_quantile_models,
)

log = get_logger(__name__)

CRAFT_KEYWORDS = (
    "handicraft",
    "showpiece",
    "home decor",
    "home furnishing",
    "craft",
)

MATERIAL_WORDS = (
    "silk",
    "cotton",
    "wool",
    "brass",
    "wood",
    "clay",
    "terracotta",
    "jute",
    "bamboo",
    "cane",
    "leather",
    "silver",
    "copper",
    "linen",
)


def _category_path(value: str) -> str:
    parts = re.findall(r'"([^"]+)"', str(value))
    return " > ".join(parts).lower()


def _guess_material(text: str) -> str:
    lowered = str(text).lower()
    for word in MATERIAL_WORDS:
        if word in lowered:
            return word
    return "unknown"


def load_craft_rows(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, low_memory=False)
    frame["category_path"] = frame["product_category_tree"].map(_category_path)

    mask = frame["category_path"].str.contains("|".join(CRAFT_KEYWORDS), na=False)
    craft = frame.loc[mask].copy()
    craft = craft.dropna(subset=["discounted_price"])
    craft = craft[craft["discounted_price"] > 0]

    log.info("loaded_craft_rows", rows=len(craft), of_total=len(frame))
    return craft


def build_training_frame(craft: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    text = craft["description"].fillna("") + " " + craft["product_specifications"].fillna("")

    items = [
        PriceInput(
            category=path.split(" > ")[1] if " > " in path else "handicraft",
            material=_guess_material(t),
            technique="unknown",
            state_code="unknown",
            # No labour data in a scrape, so hours is derived from price band
            # as a weak proxy. Replaced by the artisan's own number in
            # production, which is the number that actually sets the floor.
            hours_of_work=float(np.clip(price / 250.0, 1, 120)),
            material_cost=int(price * 0.35),
            title=str(title),
            description=str(t)[:400],
        )
        for path, t, price, title in zip(
            craft["category_path"],
            text,
            craft["discounted_price"],
            craft["product_name"].fillna(""),
            strict=False,
        )
    ]

    return to_frame(items), craft["discounted_price"].astype(float).reset_index(drop=True)


def main() -> None:
    configure_logging()

    parser = argparse.ArgumentParser(description="Train BharatSe price band models")
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--out", default=None)
    parser.add_argument("--rounds", type=int, default=400)
    args = parser.parse_args()

    craft = load_craft_rows(args.csv)
    if len(craft) < 100:
        raise SystemExit(f"Only {len(craft)} craft rows found. Check the CSV.")

    features, target = build_training_frame(craft)

    split = int(len(features) * 0.8)
    x_train, x_test = features.iloc[:split], features.iloc[split:]
    y_train, y_test = target.iloc[:split], target.iloc[split:]

    boosters = train_quantile_models(x_train, y_train, num_boost_round=args.rounds)
    out = save_models(boosters, args.out)

    preds = np.sort(
        np.vstack([boosters[q].predict(x_test) for q in QUANTILES]),  # type: ignore[attr-defined]
        axis=0,
    )
    truth = y_test.to_numpy()

    for i, q in enumerate(QUANTILES):
        log.info("pinball", quantile=q, loss=round(pinball_loss(truth, preds[i], q), 2))

    coverage = empirical_coverage(truth, preds[0], preds[2])
    log.info(
        "saved_models",
        directory=str(out),
        rows=len(features),
        coverage_p10_p90=round(coverage, 3),
        target=0.8,
    )


if __name__ == "__main__":
    main()
