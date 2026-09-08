from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.schemas.common import Health
from app.services.pricing.model import PriceBandModel

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health() -> Health:
    """Reports what is actually reachable, not just that the process is up."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - any driver error means unreachable
        # Name the host. Without it, a wrong DATABASE_URL and a network problem
        # look identical from the outside, and both just say "unreachable".
        from urllib.parse import urlsplit

        host = urlsplit(settings.DATABASE_URL).hostname or "unknown"
        database = f"unreachable ({host}): {type(exc).__name__}"

    return Health(
        status="ok",
        environment=settings.ENVIRONMENT,
        database=database,
        listing_provider=settings.LISTING_PROVIDER,
        price_model="trained" if PriceBandModel().is_trained else "not trained",
    )
