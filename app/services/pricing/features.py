"""Turning a product into the row LightGBM expects.

Kept in one place so training and inference cannot drift apart, which is the
usual way a price model quietly starts returning nonsense.
"""

from dataclasses import dataclass

import pandas as pd

CATEGORICAL = ["category", "material", "technique", "state_code"]
NUMERIC = ["hours_of_work", "material_cost", "title_length", "description_length"]
FEATURE_ORDER = NUMERIC + CATEGORICAL


@dataclass
class PriceInput:
    category: str
    material: str
    technique: str
    state_code: str
    hours_of_work: float
    material_cost: int
    title: str = ""
    description: str = ""


def to_frame(items: list[PriceInput]) -> pd.DataFrame:
    """Build the feature frame. Column order is fixed by FEATURE_ORDER."""
    rows = [
        {
            "hours_of_work": float(i.hours_of_work),
            "material_cost": float(i.material_cost),
            "title_length": float(len(i.title)),
            "description_length": float(len(i.description)),
            "category": i.category or "unknown",
            "material": i.material or "unknown",
            "technique": i.technique or "unknown",
            "state_code": i.state_code or "unknown",
        }
        for i in items
    ]

    frame = pd.DataFrame(rows, columns=FEATURE_ORDER)
    for col in CATEGORICAL:
        frame[col] = frame[col].astype("category")
    return frame
