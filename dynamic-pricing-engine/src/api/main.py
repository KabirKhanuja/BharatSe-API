from __future__ import annotations
import math
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from src.config import MODELS_DIR
from src.models.artifacts import load_artifacts, ArtefactsNotFoundError
from src.schemas.pricing import PricingRequest, PricingResult
from src.models.inference import predict_price as _infer
from src.pricing.confidence import (
    ReliabilityInputs,
    compute_reliability_score,
)


app = FastAPI(title="Dynamic Pricing Engine", version="v1")

_ARTEFACTS: Optional[dict] = None


def _load_or_503() -> dict:
    global _ARTEFACTS
    if _ARTEFACTS is not None:
        return _ARTEFACTS
    try:
        _ARTEFACTS = load_artifacts(MODELS_DIR / "v1")
        return _ARTEFACTS
    except ArtefactsNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Model artefacts not loaded: {e}")


def _reliability_from_result(out: dict) -> int:
    comparable_count = int(out.get("comparable_count") or 0)
    market_dispersion = float(out.get("market_dispersion") or 0.0) if out.get("market_dispersion") is not None else 0.0
    p10 = float(out.get("p10") or 0.0)
    p50 = float(out.get("p50") or 0.0)
    p90 = float(out.get("p90") or 0.0)
    interval_width_ratio = (p90 - p10) / p50 if p50 > 0 else 0.0
    feature_completeness = 1.0
    if "insufficient_comparables" in out.get("flags", []):
        feature_completeness = max(0.4, feature_completeness - 0.3)
    if "single_seller_risk" in out.get("flags", []):
        feature_completeness = max(0.5, feature_completeness - 0.1)
    return compute_reliability_score(ReliabilityInputs(
        comparable_count=comparable_count,
        feature_completeness=feature_completeness,
        data_recency_days=7,
        market_dispersion=market_dispersion,
        interval_width_ratio=interval_width_ratio,
    ))


def _explanation(out: dict, cost_floor: float) -> List[str]:
    parts = [f"cost_floor: ₹{int(cost_floor)}"]
    market_median = out.get("market_median")
    if market_median is not None and not (isinstance(market_median, float) and math.isnan(market_median)):
        parts.append(f"market median: ₹{int(market_median)} (n={out.get('comparable_count', 0)})")
    if out.get("flags"):
        parts.append("flags: " + ", ".join(out["flags"]))
    return parts


@app.get("/health")
def health() -> dict:
    try:
        _load_or_503()
        return {"status": "ok", "model_version": "v1"}
    except HTTPException as e:
        raise HTTPException(status_code=503, detail={"status": "unavailable", "reason": e.detail})


@app.post("/pricing/predict", response_model=PricingResult)
def predict(req: PricingRequest) -> PricingResult:
    artefacts = _load_or_503()
    request_dict = {
        **req.product.model_dump(),
        **req.cost.model_dump(),
    }
    out = _infer(request_dict, artefacts)
    cost_floor = float(out.get("cost_floor", 0.0))
    market_median = out.get("market_median")
    if market_median is not None and isinstance(market_median, float) and math.isnan(market_median):
        market_median = None
    reliability = _reliability_from_result(out)
    return PricingResult(
        recommended_price=float(out["recommended_price"]),
        recommended_price_low=float(out["p10"]),
        recommended_price_high=float(out["p90"]),
        p10=float(out["p10"]),
        p50=float(out["recommended_price"]),
        p90=float(out["p90"]),
        cost_floor=cost_floor,
        market_median=market_median,
        comparable_count=int(out.get("comparable_count", 0)),
        reliability_score=reliability,
        flags=list(out.get("flags", [])),
        explanation=_explanation({**out, "market_median": market_median}, cost_floor),
        model_version=str(artefacts.get("version", "v1")),
    )
