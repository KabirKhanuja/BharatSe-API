"""Generative product photography.

The model is handed the artisan's photo and told to redraw the object on a clean
ground. Nothing is subtracted. There is no segmentation mask, no alpha matting
and no rembg on this path.

That is a deliberate reversal of the original plan, and it is worth stating why.
A cutout is only ever as good as its edge, and the edges here are the hard
cases: loose weave, frayed silk, wicker, the fuzz on raw wool. A matte that
fails on those produces a halo, and a halo reads as fake. Redrawing sidesteps
the edge problem entirely, and also fixes the lighting, which is usually the
larger part of why a phone photo looks amateur.

The cost is that a generative model will improve things you did not ask it to
improve, which is why the prompt spends most of its length on what to preserve.
"""

from __future__ import annotations

import base64
import re

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.services.images.studio_prompt import render

log = get_logger(__name__)

_DATA_URI = re.compile(r"^data:(?P<mime>[^;,]+)?(?:;base64)?,(?P<payload>.*)$", re.S)


def decode_data_uri(value: str) -> bytes:
    """Image models hand back a base64 data URI, not raw bytes and not a path."""
    match = _DATA_URI.match(value)
    if match is None:
        raise ProviderUnavailableError("Model returned something that is not an image")
    return base64.b64decode(match.group("payload"))


def enhance(
    image: bytes,
    label: str = "",
    mime_type: str = "image/jpeg",
    aspect_ratio: str | None = None,
) -> bytes:
    """Return a catalogue ready PNG of the same object.

    Slow by the standards of everything else in this service. A single
    generation is tens of seconds, so callers must budget for it and the app
    must not sit on a spinner with no explanation.
    """
    if not settings.GEMINI_API_KEY:
        raise ProviderUnavailableError("GEMINI_API_KEY is not set")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ProviderUnavailableError(
            "google-genai is not installed. pip install '.[ai]'"
        ) from exc

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_IMAGE_MODEL,
            contents=[
                types.Part.from_bytes(data=image, mime_type=mime_type),
                render(label),
            ],
            config=types.GenerateContentConfig(
                # This has to be set explicitly. It is not implied by the model
                # name, and without it the call returns text describing the
                # image it would have made.
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio or settings.IMAGE_ASPECT_RATIO,
                ),
            ),
        )
    except Exception as exc:  # noqa: BLE001 - the SDK raises many types
        log.error("image_generation_failed", error=str(exc))
        raise ProviderUnavailableError(f"Image generation failed: {exc}") from exc

    for part in _parts(response):
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            data = inline.data
            return data if isinstance(data, bytes) else base64.b64decode(data)

    raise ProviderUnavailableError("Model returned no image")


def _parts(response: object) -> list:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    return list(getattr(content, "parts", None) or [])
