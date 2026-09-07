"""Supabase Storage.

Uploads go through the REST API with the service role key rather than the
python client, so this adds no dependency and no import that has to succeed
before the app can boot.

The service role key bypasses row level security by design. It stays on the
server and never reaches the app.
"""

from __future__ import annotations

import mimetypes
from uuid import uuid4

import httpx

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger

log = get_logger(__name__)

UPLOAD_TIMEOUT = 60


def is_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


def public_url(path: str, bucket: str | None = None) -> str:
    bucket = bucket or settings.SUPABASE_BUCKET
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def upload(
    data: bytes,
    path: str,
    content_type: str | None = None,
    bucket: str | None = None,
    upsert: bool = True,
) -> str:
    """Put bytes in the bucket and return the public URL."""
    if not is_configured():
        raise ProviderUnavailableError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY are not set"
        )

    bucket = bucket or settings.SUPABASE_BUCKET
    content_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"

    try:
        response = httpx.post(
            f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}",
            content=data,
            headers={
                "authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "content-type": content_type,
                # Without this a retry of the same upload fails with a duplicate
                # rather than replacing, which turns a flaky network into a
                # permanent error.
                "x-upsert": "true" if upsert else "false",
            },
            timeout=UPLOAD_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ProviderUnavailableError(
            f"Supabase upload failed ({exc.response.status_code}): {exc.response.text[:200]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderUnavailableError(f"Supabase upload failed: {exc}") from exc

    url = public_url(path, bucket)
    log.info("uploaded", path=path, bytes=len(data))
    return url


def product_image_path(product_id: str, kind: str, extension: str = "png") -> str:
    """Stable layout: products/<product>/<kind>/<uuid>.<ext>.

    A uuid rather than a counter, so two devices uploading at once cannot
    collide on the same key.
    """
    return f"products/{product_id}/{kind}/{uuid4().hex}.{extension}"


def fetch(url: str) -> bytes:
    """Read an image back out, for enhancing something already stored."""
    try:
        response = httpx.get(url, timeout=UPLOAD_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderUnavailableError(f"Could not fetch {url}: {exc}") from exc
    return response.content


def signed_url(path: str, bucket: str | None = None, expires_in: int = 3600) -> str | None:
    """A time limited URL for an object in a private bucket.

    Identity documents live in a private bucket on purpose, so there is no
    public URL to hand a reviewer. This mints one that expires, which means a
    link pasted into a chat or left in a browser history stops working rather
    than exposing an Aadhaar scan indefinitely.

    Returns None rather than raising: a reviewer should see a broken document
    panel, not a 500 that takes the whole queue down.
    """
    if not is_configured():
        return None

    bucket = bucket or settings.SUPABASE_BUCKET
    path = path.lstrip("/")

    try:
        response = httpx.post(
            f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}",
            json={"expiresIn": expires_in},
            headers={
                "authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "content-type": "application/json",
            },
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("sign_url_failed", path=path, bucket=bucket, error=str(exc))
        return None

    signed = response.json().get("signedURL") or response.json().get("signedUrl")
    if not signed:
        return None

    # Supabase returns a path like /object/sign/bucket/key?token=...
    return f"{settings.SUPABASE_URL}/storage/v1{signed}" if signed.startswith("/") else signed
