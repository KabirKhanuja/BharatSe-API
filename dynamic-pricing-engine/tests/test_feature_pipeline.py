from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from src.data.loaders import (
    load_synthetic_market,
    load_ecommerce,
    load_odop,
    load_synthetic_raw_material,
)
from src.features.market_features import build_market_buckets
from src.features.demand_features import build_category_aggregates
from src.features.regional_features import build_state_aggregates
from src.features.material_features import build_material_trend
from src.features.feature_pipeline import (
    InferenceRequest,
    assemble_inference_features,
)


@pytest.fixture(scope="module")
def market_df(synthetic_market_csv: Path) -> pd.DataFrame:
    return load_synthetic_market(synthetic_market_csv)


@pytest.fixture(scope="module")
def ecommerce_df(ecommerce_csv: Path) -> pd.DataFrame:
    return load_ecommerce(ecommerce_csv)


@pytest.fixture(scope="module")
def odop_df(odop_csv: Path) -> pd.DataFrame:
    return load_odop(odop_csv)


@pytest.fixture(scope="module")
def raw_df(synthetic_raw_material_csv: Path) -> pd.DataFrame:
    return load_synthetic_raw_material(synthetic_raw_material_csv)


@pytest.fixture(scope="module")
def artifacts(market_df, ecommerce_df, odop_df, raw_df):
    return {
        "market_buckets": build_market_buckets(market_df),
        "category_aggregates": build_category_aggregates(ecommerce_df),
        "state_aggregates": build_state_aggregates(odop_df),
        "material_trend": build_material_trend(raw_df),
    }


def _sample_request() -> InferenceRequest:
    return InferenceRequest(
        category="Saree",
        craft_type="Handloom",
        material="Silk",
        state="Maharashtra",
        district="Pune",
        size_m_or_units=5.5,
        weight_kg=1.2,
        handmade=True,
        quality_grade=4,
        design_complexity=3,
        raw_material_cost_inr=800.0,
        labour_cost_inr=1200.0,
        inbound_procurement_cost_inr=200.0,
        production_overhead_inr=300.0,
        season="Wedding",
    )


def test_assemble_returns_flat_dict(artifacts):
    req = _sample_request()
    out = assemble_inference_features(req, **artifacts)
    assert isinstance(out, dict)


def test_assemble_contains_cost_floor(artifacts):
    req = _sample_request()
    out = assemble_inference_features(req, **artifacts)
    assert "cost_floor_inr" in out
    assert abs(out["cost_floor_inr"] - (800 + 1200 + 200 + 300)) < 0.01


def test_assemble_contains_market_median_or_none(artifacts):
    req = _sample_request()
    out = assemble_inference_features(req, **artifacts)
    assert "market_median" in out
    assert out["market_median"] is None or out["market_median"] > 0


def test_assemble_contains_reliability_inputs(artifacts):
    req = _sample_request()
    out = assemble_inference_features(req, **artifacts)
    for k in (
        "trend_30d_pct",
        "material_trend_30d_pct",
        "demand_index",
        "comparable_count",
        "market_dispersion",
    ):
        assert k in out
