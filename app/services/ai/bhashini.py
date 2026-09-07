"""Bhashini, the MeitY language platform. Backup path, and a scoring point.

Dhruva hosts the AI4Bharat models, so this is Indian sovereign AI without us
provisioning a GPU.

The API is two steps: ask the config endpoint for an inference key and a
callback URL, then call that URL. The config call is made once at boot and
cached, because doing it per request doubles the latency for no reason. The
service ids are published, so they are pinned here rather than discovered.

Deliberately not using any of the community clients on PyPI. The best of them
takes a public HTTP URL for the audio rather than bytes, which is useless from
a phone, and it catches every exception and returns the string "API Error".
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger
from app.services.ai.provider import ListingProvider
from app.services.ai.schema import GeneratedListing

log = get_logger(__name__)

CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

ASR_SERVICE_ID = "ai4bharat/conformer-multilingual-indo_aryan-gpu--t4"
TRANSLATION_SERVICE_ID = "ai4bharat/indictrans-v2-all-gpu--t4"


class BhashiniProvider(ListingProvider):
    name = "bhashini"

    _callback_url: str | None = None
    _inference_key: str | None = None

    def healthy(self) -> bool:
        return bool(settings.BHASHINI_USER_ID and settings.BHASHINI_ULCA_API_KEY)

    def _ensure_config(self, force: bool = False) -> None:
        """Fetch and cache the inference key. Re-fetched on a 401, since the
        docs do not say whether it expires."""
        if self._callback_url and self._inference_key and not force:
            return

        payload = {
            "pipelineTasks": [{"taskType": "asr"}, {"taskType": "translation"}],
            "pipelineRequestConfig": {"pipelineId": settings.BHASHINI_PIPELINE_ID},
        }
        headers = {
            "userID": settings.BHASHINI_USER_ID,
            "ulcaApiKey": settings.BHASHINI_ULCA_API_KEY,
        }

        try:
            response = httpx.post(CONFIG_URL, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Bhashini config call failed: {exc}") from exc

        endpoint = response.json()["pipelineInferenceAPIEndPoint"]
        self._callback_url = endpoint["callbackUrl"]
        self._inference_key = endpoint["inferenceApiKey"]["value"]
        log.info("bhashini_config_cached")

    def transcribe(self, audio: bytes, source_language: str = "hi") -> str:
        if not self.healthy():
            raise ProviderUnavailableError("Bhashini credentials are not set")

        self._ensure_config()
        assert self._callback_url and self._inference_key

        body: dict[str, Any] = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": source_language},
                        "serviceId": ASR_SERVICE_ID,
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {"audio": [{"audioContent": base64.b64encode(audio).decode()}]},
        }

        try:
            response = httpx.post(
                self._callback_url,
                json=body,
                headers={"Authorization": self._inference_key},
                timeout=60,
            )
            if response.status_code == 401:
                self._ensure_config(force=True)
                response = httpx.post(
                    self._callback_url,
                    json=body,
                    headers={"Authorization": self._inference_key},
                    timeout=60,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Bhashini transcription failed: {exc}") from exc

        return response.json()["pipelineResponse"][0]["output"][0]["source"]

    def generate(
        self,
        audio: bytes,
        mime_type: str,
        language_hint: str | None = None,
    ) -> GeneratedListing:
        """Transcribe here, then write the listing with the text model.

        Bhashini transcribes and translates. It does not write a product
        listing, so the text still goes through an LLM afterwards.
        """
        transcript = self.transcribe(audio, source_language=language_hint or "hi")

        from app.services.ai.text_listing import listing_from_text

        listing = listing_from_text(transcript, language=language_hint or "hi")
        listing.transcript = transcript
        listing.detected_language = language_hint or "hi"
        return listing
