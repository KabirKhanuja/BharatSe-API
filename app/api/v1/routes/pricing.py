"""Dynamic pricing.

Returns a band and a floor, never a single number. The band is what the market
supports; the floor is what the work is worth.
"""

from fastapi import APIRouter

from app.schemas.pricing import FloorOut, PriceRequest, PriceResponse
from app.services.pricing import PriceInput, suggest_price

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/suggest", response_model=PriceResponse)
def suggest(body: PriceRequest) -> PriceResponse:
    suggestion = suggest_price(
        PriceInput(
            category=body.category,
            material=body.material,
            technique=body.technique,
            state_code=body.state_code,
            hours_of_work=body.hours_of_work,
            material_cost=body.material_cost,
            title=body.title,
            description=body.description,
        )
    )

    return PriceResponse(
        p10=suggestion.p10,
        p50=suggestion.p50,
        p90=suggestion.p90,
        floor=suggestion.floor,
        breakdown=FloorOut(**suggestion.breakdown.as_dict()),
        model_used=suggestion.model_used,
        lifted_to_floor=suggestion.lifted_to_floor,
        note=suggestion.note,
    )
