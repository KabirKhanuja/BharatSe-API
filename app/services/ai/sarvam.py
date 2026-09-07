"""Sarvam. Best Indic transcription accuracy of the three, used ASR only.

Its synchronous endpoint caps at 30 seconds of audio, so anything longer has to
be chunked or sent to the batch endpoint. A real voice note will exceed that,
which is why this is a fallback rather than the default.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.services.ai.provider import ListingProvider
from app.services.ai.schema import GeneratedListing

log = get_logger(__name__)

STT_URL = "https://api.sarvam.ai/speech-to-text"
MAX_SYNC_SECONDS = 30


class SarvamProvider(ListingProvider):
    name = "sarvam"

    def healthy(self) -> bool:
        return bool(settings.SARVAM_API_KEY)

    def transcribe(self, audio: bytes, language: str = "hi-IN") -> str:
        if not self.healthy():
            raise ProviderUnavailableError("SARVAM_API_KEY is not set")

        try:
            response = httpx.post(
                STT_URL,
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                files={"file": ("audio.wav", audio, "audio/wav")},
                data={"language_code": language, "model": "saarika:v2"},
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Sarvam transcription failed: {exc}") from exc

        return response.json().get("transcript", "")

    def generate(
        self,
        audio: bytes,
        mime_type: str,
        language_hint: str | None = None,
    ) -> GeneratedListing:
        transcript = self.transcribe(audio, language=language_hint or "hi-IN")

        from app.services.ai.text_listing import listing_from_text

        listing = listing_from_text(transcript, language=language_hint or "hi")
        listing.transcript = transcript
        listing.detected_language = language_hint or "hi"
        return listing
