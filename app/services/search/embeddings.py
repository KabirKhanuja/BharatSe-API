"""CLIP embeddings for search.

One model handles both an uploaded image and a typed or spoken query, and puts
them in the same 512 dimensional space. That symmetry is the whole feature:
text search and image search hit identical SQL downstream.

Embeddings are computed when a product is saved, never on the request path.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.errors import ProviderUnavailableError
from app.core.logging import get_logger

log = get_logger(__name__)

MODEL_NAME = "clip-ViT-B-32"
EMBEDDING_DIM = 512


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ProviderUnavailableError(
            "sentence-transformers is not installed. pip install '.[ai]'"
        ) from exc

    log.info("loading_clip_model", model=MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    return _model().encode(text).tolist()


def embed_image(image_bytes: bytes) -> list[float]:
    import io

    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return _model().encode(image).tolist()
