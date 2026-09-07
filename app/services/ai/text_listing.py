"""Turn a transcript into a listing.

Only used on the fallback paths. On the Gemini path the audio goes straight to
the listing in one call and this is never reached.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.services.ai.schema import GeneratedListing

PROMPT = """An Indian artisan described her handmade product. This is what she said:

"{transcript}"

Write a product listing from it. Only use facts she stated, never invent a
material, a size or a place. Give both English and Hindi, each written naturally
rather than translated from the other.
"""


def listing_from_text(transcript: str, language: str = "hi") -> GeneratedListing:
    if not transcript.strip():
        raise ProviderUnavailableError("Empty transcript, nothing to write a listing from")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ProviderUnavailableError("google-genai is not installed") from exc

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=PROMPT.format(transcript=transcript),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedListing,
        ),
    )

    if response.parsed is None:
        raise ProviderUnavailableError("Model returned no parsable listing")
    return response.parsed
