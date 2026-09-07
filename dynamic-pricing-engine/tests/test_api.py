from __future__ import annotations
from pathlib import Path
import math
import pytest

from src.schemas.pricing import PricingRequest, PricingResult, ProductFeatures, CostFeatures


@pytest.fixture(scope="module")
def artefacts_dir(tmp_path_factory):
    from src.models.artifacts import save_artifacts
    import lightgbm as lgb
    import numpy as np
    import pandas as pd

    out = tmp_path_factory.mktemp("api_models") / "v1"
    rng = np.random.default_rng(42)
    n = 200
    cols_numeric = [f"f{i}" for i in range(29)]
    cat_levels = {
        "category": ["Saree", "Bag", "Basketry", "Jewellery", "__missing__"],
        "craft_type": ["Handloom", "Basketry", "Embroidery", "__missing__"],
        "material": ["Silk", "Cotton", "Jute", "Bamboo", "__missing__"],
        "state": ["Maharashtra", "Gujarat", "Karnataka", "__missing__"],
        "district": ["Pune", "Surat", "Bengaluru", "__missing__"],
        "season": ["Wedding", "Normal", "Monsoon", "__missing__"],
    }
    cat_cols = list(cat_levels.keys())
    Xn = pd.DataFrame(rng.normal(size=(n, 29)), columns=cols_numeric).astype(np.float32)
    Xc = pd.DataFrame({
        c: pd.Categorical(rng.choice(levels[:-1], size=n), categories=levels)
        for c, levels in cat_levels.items()
    })
    X = pd.concat([Xn, Xc], axis=1)
    y = rng.normal(size=n) * 100 + 2500
    p50 = lgb.LGBMRegressor(n_estimators=20, random_state=42, verbose=-1).fit(X, y)
    p10 = lgb.LGBMRegressor(objective="quantile", alpha=0.10, n_estimators=20, random_state=42, verbose=-1).fit(X, y)
    p50q = lgb.LGBMRegressor(objective="quantile", alpha=0.50, n_estimators=20, random_state=42, verbose=-1).fit(X, y)
    p90 = lgb.LGBMRegressor(objective="quantile", alpha=0.90, n_estimators=20, random_state=42, verbose=-1).fit(X, y)
    save_artifacts(
        {"p50": p50, "p10": p10, "p50_quantile": p50q, "p90": p90},
        list(X.columns),
        cat_levels,
        {},
        out,
    )
    return out


@pytest.fixture
def client(artefacts_dir, monkeypatch):
    import importlib
    monkeypatch.setattr("src.config.MODELS_DIR", artefacts_dir.parent)
    from fastapi.testclient import TestClient
    from src.api import main
    importlib.reload(main)
    return TestClient(main.app)


def _valid_request_dict() -> dict:
    return {
        "product": {
            "category": "Saree",
            "craft_type": "Handloom",
            "material": "Silk",
            "state": "Maharashtra",
            "district": "Pune",
            "size_m_or_units": 5.5,
            "weight_kg": 1.2,
            "handmade": True,
            "quality_grade": 4,
            "design_complexity": 3,
            "season": "Wedding",
        },
        "cost": {
            "raw_material_cost_inr": 800.0,
            "labour_cost_inr": 1200.0,
            "inbound_procurement_cost_inr": 200.0,
            "production_overhead_inr": 300.0,
        },
    }


def test_pricing_request_round_trip():
    req = PricingRequest(**_valid_request_dict())
    dumped = req.model_dump()
    assert "product" in dumped and "cost" in dumped
    assert dumped["product"]["category"] == "Saree"


def test_pricing_result_field_types():
    result = PricingResult(
        recommended_price=2500.0,
        recommended_price_low=2200.0,
        recommended_price_high=2800.0,
        p10=2200.0,
        p50=2500.0,
        p90=2800.0,
        cost_floor=2000.0,
        market_median=2400.0,
        comparable_count=42,
        reliability_score=78,
        flags=[],
        explanation=["cost floor 2000", "market median 2400"],
        model_version="v1",
    )
    assert result.recommended_price == 2500.0
    assert result.comparable_count == 42
    assert result.reliability_score == 78
    assert result.model_version == "v1"


def test_pricing_request_rejects_negative_cost():
    bad = _valid_request_dict()
    bad["cost"]["raw_material_cost_inr"] = -1.0
    with pytest.raises(Exception):
        PricingRequest(**bad)


def test_pricing_request_rejects_quality_out_of_range():
    bad = _valid_request_dict()
    bad["product"]["quality_grade"] = 7
    with pytest.raises(Exception):
        PricingRequest(**bad)


def test_pricing_request_rejects_missing_required_field():
    bad = _valid_request_dict()
    bad["product"].pop("category")
    with pytest.raises(Exception):
        PricingRequest(**bad)


def test_pricing_request_accepts_optional_season_none():
    d = _valid_request_dict()
    d["product"]["season"] = None
    req = PricingRequest(**d)
    assert req.product.season is None


def test_pricing_result_serialises_to_dict():
    result = PricingResult(
        recommended_price=2500.0,
        recommended_price_low=2200.0,
        recommended_price_high=2800.0,
        p10=2200.0,
        p50=2500.0,
        p90=2800.0,
        cost_floor=2000.0,
        comparable_count=42,
        reliability_score=78,
    )
    d = result.model_dump()
    assert d["recommended_price"] == 2500.0
    assert d["flags"] == []


def test_pricing_result_quantile_ordering_invariant():
    result = PricingResult(
        recommended_price=2500.0,
        recommended_price_low=2200.0,
        recommended_price_high=2800.0,
        p10=2200.0,
        p50=2500.0,
        p90=2800.0,
        cost_floor=2000.0,
        comparable_count=42,
        reliability_score=78,
    )
    assert result.p10 <= result.p50 <= result.p90
    assert result.recommended_price_low <= result.recommended_price <= result.recommended_price_high


def test_product_features_district_required():
    with pytest.raises(Exception):
        ProductFeatures(
            category="Saree",
            craft_type="Handloom",
            material="Silk",
            state="Maharashtra",
            size_m_or_units=5.5,
            weight_kg=1.2,
            handmade=True,
            quality_grade=4,
            design_complexity=3,
        )


def test_health_returns_ok_when_artefacts_present(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_version"] == "v1"


def test_predict_returns_pricing_result(client):
    r = client.post("/pricing/predict", json=_valid_request_dict())
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ("recommended_price", "p10", "p50", "p90", "cost_floor", "reliability_score"):
        assert k in body
    assert body["p10"] <= body["p50"] <= body["p90"]
    assert body["recommended_price"] > 0
    assert 0 <= body["reliability_score"] <= 100


def test_predict_rejects_missing_field(client):
    bad = _valid_request_dict()
    bad["product"].pop("category")
    r = client.post("/pricing/predict", json=bad)
    assert r.status_code == 422


def test_predict_rejects_negative_cost(client):
    bad = _valid_request_dict()
    bad["cost"]["raw_material_cost_inr"] = -1.0
    r = client.post("/pricing/predict", json=bad)
    assert r.status_code == 422


def test_predict_accepts_unknown_category(client):
    req = _valid_request_dict()
    req["product"]["category"] = "__definitely_unknown__"
    r = client.post("/pricing/predict", json=req)
    assert r.status_code == 200, r.text


def test_health_returns_503_when_artefacts_missing(monkeypatch, tmp_path):
    import importlib
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    from fastapi.testclient import TestClient
    from src.api import main
    importlib.reload(main)
    c = TestClient(main.app)
    r = c.get("/health")
    assert r.status_code == 503
