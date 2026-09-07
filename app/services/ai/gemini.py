"""Gemini. One call takes the artisan's audio and returns the whole listing.

This replaces a three step chain of speech to text, then translation, then
generation. Fewer moving parts, one network round trip instead of three, and
the two languages come out of the same pass so they stay consistent.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.services.ai.provider import ListingProvider
from app.services.ai.schema import GeneratedListing

log = get_logger(__name__)

PROMPT = """You are helping an Indian artisan list a handmade product for sale.

The audio is the maker describing her own product, in her own language. It may
be Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati, Kannada, Odia or Punjabi.

Write a listing from what she says. Rules:
1. Only use facts she states. Never invent a material, a size or a place.
2. Write both English and Hindi. Neither is a translation of the other, both
   describe the same object naturally in that language.
3. The description should read like a person wrote it, not like an
   advertisement. Two or three sentences.
4. Tags should be words a buyer would actually search for.
5. If she mentions how long it took, put that in estimated_hours.
6. Put what you heard, in her own language, in transcript.
"""


class GeminiProvider(ListingProvider):
    name = "gemini"

    def healthy(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def generate(
        self,
        audio: bytes,
        mime_type: str,
        language_hint: str | None = None,
    ) -> GeneratedListing:
        if not self.healthy():
            raise ProviderUnavailableError("GEMINI_API_KEY is not set")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderUnavailableError(
                "google-genai is not installed. pip install '.[ai]'"
            ) from exc

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = PROMPT
        if language_hint:
            prompt += f"\nShe is most likely speaking {language_hint}."

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=audio, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedListing,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - upstream raises many types
            log.error("gemini_call_failed", error=str(exc))
            raise ProviderUnavailableError(f"Gemini call failed: {exc}") from exc

        parsed = response.parsed
        if parsed is None:
            raise ProviderUnavailableError("Gemini returned no parsable listing")

        log.info("listing_generated", provider=self.name)
        return parsed
