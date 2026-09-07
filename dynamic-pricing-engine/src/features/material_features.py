from __future__ import annotations
from typing import Any
import pandas as pd


class UnknownMaterialError(KeyError):
    pass


def build_material_trend(raw_material: pd.DataFrame) -> pd.DataFrame:
    df = raw_material.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    latest = df.groupby(["state", "material"], observed=True).tail(1)
    latest = latest[["state", "material", "date", "modal_price_inr_per_unit"]].rename(
        columns={"modal_price_inr_per_unit": "material_price_latest",
                 "date": "material_price_latest_date"}
    )

    def _delta(g: pd.DataFrame) -> float:
        g = g.sort_values("date")
        if len(g) < 2:
            return 0.0
        last = g["modal_price_inr_per_unit"].iloc[-1]
        prev = g["modal_price_inr_per_unit"].iloc[0]
        if prev == 0:
            return 0.0
        return float((last - prev) / prev)

    trend_30d = (
        df.groupby(["state", "material"], observed=True)
          .apply(_delta, include_groups=False)
          .rename("material_trend_30d_pct")
    )

    out = latest.merge(trend_30d, on=["state", "material"], how="left")
    out = out.set_index(["state", "material"])
    return out


def lookup_material_trend(trend: pd.DataFrame, state: str, material: str) -> dict:
    try:
        row = trend.loc[(state, material)]
    except KeyError as e:
        raise UnknownMaterialError(f"No material trend for ({state!r}, {material!r})") from e
    return {
        "material_price_latest": float(row["material_price_latest"]),
        "material_trend_30d_pct": float(row["material_trend_30d_pct"]),
        "material_price_latest_date": row["material_price_latest_date"],
    }
