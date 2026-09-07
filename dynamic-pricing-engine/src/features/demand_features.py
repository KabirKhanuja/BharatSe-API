from __future__ import annotations
import pandas as pd


_EC_CATEGORY_LABELS = {
    0: "category_0",
    1: "category_1",
    2: "category_2",
    3: "category_3",
    4: "category_4",
    5: "category_5",
    6: "category_6",
    7: "category_7",
}


def category_id_to_label(ecommerce: pd.DataFrame) -> dict:
    ids = sorted(ecommerce["product_category"].dropna().unique().tolist())
    return {i: _EC_CATEGORY_LABELS.get(i, f"category_{i}") for i in ids}


def build_category_aggregates(ecommerce: pd.DataFrame) -> pd.DataFrame:
    g = ecommerce.groupby("product_category", observed=True)
    out = pd.DataFrame({
        "ec_purchase_rate": g["purchased"].mean(),
        "ec_avg_unit_price": g["unit_price"].mean(),
        "ec_avg_discount": g["discount_percent"].mean(),
        "ec_avg_rating": g["rating"].mean(),
        "ec_visit_count": g.size(),
    })
    out["ec_price_volatility"] = g["unit_price"].std(ddof=0) / g["unit_price"].mean()
    out["ec_price_volatility"] = out["ec_price_volatility"].fillna(0.0)
    out["ec_category_label"] = pd.Series(
        {i: _EC_CATEGORY_LABELS.get(i, f"category_{i}") for i in out.index}
    )
    return out


def build_category_month_aggregates(ecommerce: pd.DataFrame) -> pd.DataFrame:
    g = ecommerce.groupby(["product_category", "visit_month"], observed=True)
    out = pd.DataFrame({
        "ec_monthly_purchase_rate": g["purchased"].mean(),
        "ec_monthly_visit_count": g.size(),
        "ec_monthly_avg_unit_price": g["unit_price"].mean(),
    })
    out["ec_category_label"] = pd.Series(
        {idx: _EC_CATEGORY_LABELS.get(idx[0], f"category_{idx[0]}")
         for idx in out.index}
    )
    return out
