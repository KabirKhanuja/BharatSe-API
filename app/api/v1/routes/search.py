"""Search. Text and image hit the same query.

CLIP puts both into one 512 dimensional space, so `GET /search?q=blue pottery`
and an uploaded photo run identical SQL downstream. pgvector with an HNSW index
does the nearest neighbour lookup.

HNSW rather than IVFFlat on purpose: IVFFlat has to be built after data exists,
so creating it in a migration on an empty table produces meaningless centroids
and silently wrong neighbours.
"""

from fastapi import APIRouter, File, Query, UploadFile

from app.api.deps import SessionDep
from app.core.errors import ProviderUnavailableError

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search_text(
    session: SessionDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, le=50),
) -> dict:
    try:
        from app.services.search.embeddings import embed_text

        vector = embed_text(q)
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc

    # TODO: once product_embeddings is migrated in, this becomes
    # ORDER BY embedding <=> :vector LIMIT :limit
    return {"query": q, "dimensions": len(vector), "results": [], "limit": limit}


@router.post("/by-image")
async def search_by_image(session: SessionDep, image: UploadFile = File(...)) -> dict:
    try:
        from app.services.search.embeddings import embed_image

        vector = embed_image(await image.read())
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc

    return {"dimensions": len(vector), "results": []}
