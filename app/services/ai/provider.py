"""The interface every language provider implements.

Written before any provider so swapping one at 3am is a config change and not
a rewrite. Gemini is the default because a single call takes the audio and
returns the finished listing. Bhashini and Sarvam are adapters for when it is
rate limited, blocked on the venue network, or when a government panel wants to
see Indian sovereign AI in the stack.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.services.ai.schema import GeneratedListing


class ListingProvider(ABC):
    name: str

    @abstractmethod
    def generate(
        self, audio: bytes, mime_type: str, language_hint: str | None = None
    ) -> GeneratedListing:
        """Turn a voice note into a validated listing."""

    @abstractmethod
    def healthy(self) -> bool:
        """Whether this provider is configured well enough to try."""


def get_provider(name: str | None = None) -> ListingProvider:
    """Resolve the configured provider, importing lazily so the API boots
    without the heavy AI extras installed."""
    chosen = (name or settings.LISTING_PROVIDER).lower()

    if chosen == "gemini":
        from app.services.ai.gemini import GeminiProvider

        return GeminiProvider()
    if chosen == "bhashini":
        from app.services.ai.bhashini import BhashiniProvider

        return BhashiniProvider()
    if chosen == "sarvam":
        from app.services.ai.sarvam import SarvamProvider

        return SarvamProvider()

    raise ProviderUnavailableError(f"Unknown listing provider: {chosen}")


def get_provider_with_fallback(order: list[str] | None = None) -> ListingProvider:
    """First healthy provider in order of preference."""
    for name in order or [settings.LISTING_PROVIDER, "bhashini", "sarvam"]:
        try:
            provider = get_provider(name)
        except ProviderUnavailableError:
            continue
        if provider.healthy():
            return provider

    raise ProviderUnavailableError("No language provider is configured and reachable")
