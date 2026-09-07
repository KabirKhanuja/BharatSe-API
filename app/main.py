"""FastAPI application.

One door. The mobile app never calls an AI service directly, which is what lets
us swap a model later without shipping an app update to a phone that may never
receive one.
"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info(
        "starting",
        environment=settings.ENVIRONMENT,
        listing_provider=settings.LISTING_PROVIDER,
    )
    yield
    log.info("stopping")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Listings and dashboard payloads are mostly text, and the artisan is often on
# a thin connection, so compression is worth more here than usual.
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Give every request an id and log how long it took.

    The id goes back in a header, so a report of "it failed on my phone" can be
    traced to one line in the logs.
    """
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()

    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = str(elapsed_ms)

    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ms=elapsed_ms,
    )
    return response


@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """The database being unreachable is a 503, not a 500.

    A 500 tells the caller we are broken. A 503 tells it to try again, which is
    what the phone\'s outbox already knows how to do.
    """
    log.error("database_unreachable", path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "code": "database_unavailable",
            "message": "The service is temporarily unable to reach its database.",
        },
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Errors we raise on purpose become a stable JSON shape the app can read."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": settings.PROJECT_NAME, "docs": "/docs"}
