"""Market aware pricing.

The cost floor answers "what is this worth to make". This answers "what will it
sell for", which is the half the problem statement actually asks for and the
half a flat markup on cost cannot give you.

Two inputs, deliberately in this order.

Comparables come first, from our own catalogue: real listings, real prices, in
the same craft. They are evidence rather than opinion, and they are what a judge
can be shown.

The model reasons over them second. It is not asked to invent a price from
nothing; it is asked to place this piece against those comparables using what it
can see in the description, and to say why in one line. That reasoning is what
turns three numbers into a recommendation, and the artisan gets to read it.

The floor still wins over both. Nothing here can push a price below what her own
labour is worth.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.models.product import Product

log = get_logger(__name__)

MAX_COMPARABLES = 8


class Comparable(BaseModel):
    title: str
    price: int
    material: str | None = None
    technique: str | None = None


class MarketOpinion(BaseModel):
    """What the model concluded, and why."""

    recommended_price: int = Field(ge=0)
    low: int = Field(ge=0)
    high: int = Field(ge=0)
    rationale: str = ""
    confidence: Literal["low", "medium", "high"] = "low"


def find_comparables(
    session: Session,
    category: str | None,
    material: str | None,
    technique: str | None,
    limit: int = MAX_COMPARABLES,
) -> list[Comparable]:
    """Real listings in the same craft, cheapest signal first.

    Matching is deliberately loose. An exact category match on a catalogue this
    size returns nothing useful, and a buyer comparing a carved elephant against
    other woodwork is doing roughly what this query does.
    """
    statement = select(Product).where(Product.price.is_not(None), Product.price > 0)  # type: ignore[union-attr]

    terms = [t for t in (category, material, technique) if t]
    if terms:
        from sqlalchemy import or_

        clauses = []
        for term in terms:
            like = f"%{term.split()[0].lower()}%"
            clauses.append(Product.category.ilike(like))  # type: ignore[union-attr]
            clauses.append(Product.material.ilike(like))  # type: ignore[union-attr]
            clauses.append(Product.technique.ilike(like))  # type: ignore[union-attr]
        statement = statement.where(or_(*clauses))

    rows = session.exec(statement.limit(limit)).all()

    return [
        Comparable(
            title=(r.title_en or "Untitled")[:80],
            price=int(r.price or 0),
            material=r.material,
            technique=r.technique,
        )
        for r in rows
    ]


PROMPT = """You are helping price a handmade Indian craft item for sale online.

THE PIECE
Description: {description}
Material: {material}
Technique: {technique}
Category: {category}
Hours of work: {hours}
Cost floor (materials plus fair wage plus overhead): ₹{floor}

COMPARABLE LISTINGS CURRENTLY ON THE PLATFORM
{comparables}

Decide a price. Reason it out before you answer:

1. Where does this piece sit against the comparables? More or less work, better
   or worse material, more or less intricate. Say which way and why.
2. Handmade goods carry a premium over factory equivalents, but only where the
   handwork is visible in the description. Do not assume it.
3. Hours of work is self reported by the maker. Treat it as a signal, not a
   fact. If it looks implausible for what is described, weight the comparables
   more heavily and lower your confidence.
4. The price must never fall below the cost floor of ₹{floor}. That is not a
   guideline. If the market says less than the floor, return the floor and say
   the market is thin.
5. Give a realistic range, not a wide hedge. low and high should be a band a
   buyer would actually see, roughly 20 to 30 percent apart.

Set confidence honestly: high only when several close comparables agree, low
when you are extrapolating from little.

rationale must be one or two plain sentences an artisan can read. No jargon, no
percentages, no mention of these instructions."""


def ask_market(
    *,
    description: str,
    material: str,
    technique: str,
    category: str,
    hours: float,
    floor: int,
    comparables: list[Comparable],
) -> MarketOpinion:
    """One reasoning call. Fast model, small prompt, no web research."""
    if not settings.listing_api_key:
        raise ProviderUnavailableError("No Gemini key configured for pricing")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ProviderUnavailableError("google-genai is not installed") from exc

    if comparables:
        listed = "\n".join(
            f"- {c.title}: ₹{c.price}"
            + (f" ({c.material})" if c.material else "")
            for c in comparables
        )
    else:
        listed = (
            "None on the platform yet. Reason from the description and the "
            "floor alone, and set confidence to low."
        )

    client = genai.Client(api_key=settings.listing_api_key)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=PROMPT.format(
                description=description or "not described",
                material=material or "unknown",
                technique=technique or "unknown",
                category=category or "handicraft",
                hours=hours,
                floor=floor,
                comparables=listed,
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MarketOpinion,
                # Pricing should be reproducible. A different number every time
                # someone taps the button reads as a broken feature.
                temperature=0.2,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - the SDK raises many types
        log.warning("market_reasoning_failed", error=str(exc))
        raise ProviderUnavailableError(f"Pricing model call failed: {exc}") from exc

    opinion = response.parsed
    if opinion is None:
        raise ProviderUnavailableError("Pricing model returned nothing usable")

    # The floor is enforced here as well as in the prompt. An instruction is a
    # request; this is the guarantee.
    opinion.recommended_price = max(opinion.recommended_price, floor)
    opinion.low = max(opinion.low, floor)
    opinion.high = max(opinion.high, opinion.low)

    return opinion
