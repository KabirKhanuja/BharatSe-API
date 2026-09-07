from pydantic import BaseModel, Field


class PriceRequest(BaseModel):
    category: str = "other"
    material: str = "unknown"
    technique: str = "unknown"
    state_code: str = "unknown"
    hours_of_work: float = Field(ge=0)
    material_cost: int = Field(ge=0)
    title: str = ""
    description: str = ""


class FloorOut(BaseModel):
    material_cost: int
    labour_cost: int
    overhead: int
    floor: int
    wage_per_hour: int
    hours: float


class ComparableOut(BaseModel):
    title: str
    price: int
    material: str | None = None


class PriceResponse(BaseModel):
    p10: int
    p50: int
    p90: int
    floor: int
    breakdown: FloorOut
    model_used: bool
    lifted_to_floor: bool
    note: str

    # How the number was actually reached, so the app can say so rather than
    # presenting arithmetic as market analysis.
    method: str = "cost"
    rationale: str = ""
    confidence: str = "low"
    comparables: list[ComparableOut] = []
