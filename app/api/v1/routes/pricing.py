"""Dynamic pricing.

Returns a band and a floor, never a single number. The band is what the market
supports; the floor is what the work is worth.
"""

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.schemas.pricing import ComparableOut, FloorOut, PriceRequest, PriceResponse
from app.services.pricing import PriceInput, suggest_price
from app.services.pricing.market import ask_market, find_comparables

log = get_logger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/suggest", response_model=PriceResponse)
def suggest(body: PriceRequest, session: SessionDep) -> PriceResponse:
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

    comparables = find_comparables(
        session, body.category, body.material, body.technique
    )

    # Ask the model to place this piece against real listings. If it is
    # unreachable we still return the cost based band rather than an error,
    # because an artisan waiting on a bad connection needs a number.
    p10, p50, p90 = suggestion.p10, suggestion.p50, suggestion.p90
    method, rationale, confidence = "cost", "", "low"

    try:
        opinion = ask_market(
            description=body.description,
            material=body.material,
            technique=body.technique,
            category=body.category,
            hours=body.hours_of_work,
            floor=suggestion.floor,
            comparables=comparables,
        )
        p10, p50, p90 = opinion.low, opinion.recommended_price, opinion.high
        method = "market" if comparables else "reasoned"
        rationale, confidence = opinion.rationale, opinion.confidence
    except ProviderUnavailableError as exc:
        log.info("pricing_fell_back_to_cost", reason=exc.message)

    lifted = p10 <= suggestion.floor

    return PriceResponse(
        p10=p10,
        p50=p50,
        p90=p90,
        floor=suggestion.floor,
        breakdown=FloorOut(**suggestion.breakdown.as_dict()),
        model_used=suggestion.model_used,
        lifted_to_floor=lifted,
        note=rationale or suggestion.note,
        method=method,
        rationale=rationale,
        confidence=confidence,
        comparables=[
            ComparableOut(title=c.title, price=c.price, material=c.material)
            for c in comparables
        ],
    )
