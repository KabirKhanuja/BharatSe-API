"""Image studio, server side."""

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api.deps import CurrentArtisan
from app.core.errors import AppError, ProviderUnavailableError
from app.services.images.background import remove_background
from app.services.images.enhance import auto_correct, compose_on_canvas

router = APIRouter(prefix="/images", tags=["images"])

MAX_IMAGE_BYTES = 12 * 1024 * 1024


async def _read(upload: UploadFile) -> bytes:
    payload = await upload.read()
    if not payload:
        raise AppError("Empty image upload").as_http()
    if len(payload) > MAX_IMAGE_BYTES:
        raise AppError("Image is too large").as_http()
    return payload


@router.post("/cutout")
async def cutout(artisan: CurrentArtisan, image: UploadFile = File(...)) -> Response:
    """Higher quality cutout than the one the phone already produced."""
    try:
        result = remove_background(await _read(image))
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc
    return Response(content=result, media_type="image/png")


@router.post("/studio")
async def studio(
    artisan: CurrentArtisan,
    image: UploadFile = File(...),
    aspect: str = Form(default="square"),
) -> Response:
    """The full pass: cut out, correct, and place on a clean canvas."""
    payload = await _read(image)
    try:
        corrected = auto_correct(payload)
        cut = remove_background(corrected)
        composed = compose_on_canvas(cut, aspect=aspect)
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc
    return Response(content=composed, media_type="image/jpeg")
