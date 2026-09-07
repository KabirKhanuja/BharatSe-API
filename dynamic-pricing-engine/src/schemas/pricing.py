from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, conint, confloat


class ProductFeatures(BaseModel):
    category: str
    craft_type: str
    material: str
    state: str
    district: str
    size_m_or_units: confloat(ge=0)
    weight_kg: confloat(ge=0)
    handmade: bool
    quality_grade: conint(ge=1, le=5)
    design_complexity: conint(ge=1, le=5)
    season: Optional[str] = None


class CostFeatures(BaseModel):
    raw_material_cost_inr: confloat(ge=0)
    labour_cost_inr: confloat(ge=0)
    inbound_procurement_cost_inr: confloat(ge=0)
    production_overhead_inr: confloat(ge=0)


class PricingRequest(BaseModel):
    product: ProductFeatures
    cost: CostFeatures


class PricingResult(BaseModel):
    recommended_price: float
    recommended_price_low: float
    recommended_price_high: float
    p10: float
    p50: float
    p90: float
    cost_floor: float
    market_median: Optional[float] = None
    comparable_count: int
    reliability_score: int
    flags: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)
    model_version: str = "v1"
