from __future__ import annotations
import pandas as pd


class UnknownRegionError(KeyError):
    pass


def build_state_aggregates(odop: pd.DataFrame) -> pd.DataFrame:
    g = odop.groupby("State", observed=True)
    out = pd.DataFrame({
        "odop_state_product_count": g.size(),
        "odop_state_gi_count": (g["GI Status"].apply(lambda s: (s == "Yes").sum())),
        "odop_state_sector_count": g["Sector"].nunique(),
    })
    out.index.name = "state"
    return out
