"""Background removal, server side.

The phone already produced a fast cutout before upload, so this pass is about
quality rather than speed.

The model is named explicitly and must stay that way. rembg's default is now
BRIA RMBG, which requires a paid commercial agreement. Calling remove() with no
session ships a model we are not licensed to ship, on a government problem
statement. isnet-general-use is Apache 2.0 and good on textile and jewellery
edges.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _session():
    try:
        from rembg import new_session
    except ImportError as exc:
        raise ProviderUnavailableError("rembg is not installed. pip install '.[ai]'") from exc

    log.info("rembg_session_created", model=settings.REMBG_MODEL)
    return new_session(settings.REMBG_MODEL)


def remove_background(image_bytes: bytes) -> bytes:
    """Return a PNG with an alpha channel."""
    try:
        from rembg import remove
    except ImportError as exc:
        raise ProviderUnavailableError("rembg is not installed. pip install '.[ai]'") from exc

    return remove(
        image_bytes,
        session=_session(),
        # Kills the coloured halo that soft fabric edges otherwise pick up.
        post_process_mask=True,
    )
