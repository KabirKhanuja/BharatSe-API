"""Voice note to listing."""

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentArtisan
from app.core.errors import AppError, ProviderUnavailableError
from app.core.logging import get_logger
from app.schemas.listing import ListingResponse
from app.services.ai.provider import get_provider_with_fallback

router = APIRouter(prefix="/listings", tags=["listings"])
log = get_logger(__name__)

MAX_AUDIO_BYTES = 15 * 1024 * 1024


@router.post("/generate", response_model=ListingResponse)
async def generate_listing(
    artisan: CurrentArtisan,
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> ListingResponse:
    """She talks, this returns a finished listing in English and Hindi.

    The phone records 16 kHz mono WAV natively, which is exactly what every
    provider wants, so there is no conversion step anywhere in this path.
    """
    payload = await audio.read()
    if not payload:
        raise AppError("Empty audio upload").as_http()
    if len(payload) > MAX_AUDIO_BYTES:
        raise AppError("Audio is too large. Keep voice notes under two minutes.").as_http()

    try:
        provider = get_provider_with_fallback()
        listing = provider.generate(
            payload,
            mime_type=audio.content_type or "audio/wav",
            language_hint=language,
        )
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc

    log.info("listing_generated", artisan_id=str(artisan.id), provider=provider.name)
    return ListingResponse(listing=listing, provider=provider.name)
