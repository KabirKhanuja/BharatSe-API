"""Artisan identity verification.

The half the ministry queue was missing. `ministry.py` could already list and
approve artisans, but nothing anywhere wrote `verification_document_url`, so
the queue could only ever show rows inserted by hand.

An identity document is not a product photo. It goes to a private bucket, it is
never returned as a public URL to the artisan, and the only people who read it
are reviewing it.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlmodel import select

from app.api.deps import CurrentArtisan, SessionDep
from app.core.errors import AppError, ProviderUnavailableError
from app.core.logging import get_logger
from app.models.artisan import ArtisanProfile
from app.schemas.verification_submit import VerificationStatus, VerificationSubmitted
from app.services.storage import supabase

router = APIRouter(prefix="/verification", tags=["verification"])
log = get_logger(__name__)

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp", "application/pdf"}

# Magic bytes, checked because a client-supplied content type is a label and not
# evidence. Flutter's MultipartFile does not infer one at all and sends
# application/octet-stream, so a header check alone rejects perfectly good JPEGs.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
)


def sniff_type(payload: bytes, declared: str | None, filename: str | None) -> str | None:
    """Work out what this actually is, preferring the bytes over the label."""
    for signature, mime in _SIGNATURES:
        if payload.startswith(signature):
            if mime == "image/webp" and payload[8:12] != b"WEBP":
                continue
            return mime

    # HEIC has its marker at offset 4 rather than 0.
    if payload[4:8] == b"ftyp" and payload[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return "image/heic"

    if declared in ALLOWED_TYPES:
        return declared

    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed in ALLOWED_TYPES:
            return guessed

    return None

# Separate from product-assets, which is public. Identity documents must not be
# readable by anyone holding a guessable URL.
DOCUMENT_BUCKET = "verification-documents"


def _profile_for(session: SessionDep, artisan_id) -> ArtisanProfile:
    profile = session.exec(
        select(ArtisanProfile).where(ArtisanProfile.user_id == artisan_id)
    ).first()

    if profile is None:
        # First submission creates the profile. An artisan reaches this screen
        # straight after signing in, before she has one.
        profile = ArtisanProfile(user_id=artisan_id, state_code="XX")
        session.add(profile)
        session.commit()
        session.refresh(profile)

    return profile


@router.get("/status", response_model=VerificationStatus)
def status(artisan: CurrentArtisan, session: SessionDep) -> VerificationStatus:
    """What the app polls to decide which screen to show."""
    profile = session.exec(
        select(ArtisanProfile).where(ArtisanProfile.user_id == artisan.id)
    ).first()

    submitted = bool(profile and profile.verification_document_url)
    verified = bool(profile and profile.is_verified)

    return VerificationStatus(
        submitted=submitted,
        is_verified=verified,
        state=("approved" if verified else "pending" if submitted else "not_submitted"),
    )


@router.post("/submit", response_model=VerificationSubmitted)
async def submit(
    artisan: CurrentArtisan,
    session: SessionDep,
    document: UploadFile = File(...),
    state_code: str = Form(default=""),
    craft: str = Form(default=""),
    district: str = Form(default=""),
    cluster: str = Form(default=""),
) -> VerificationSubmitted:
    """Upload an identity document for review.

    Re-submitting replaces the previous document rather than adding a second
    one, because a reviewer looking at two documents does not know which is
    current.
    """
    payload = await document.read()
    if not payload:
        raise AppError("Empty document upload").as_http()
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise AppError("Document is too large. Keep it under 8 MB.").as_http()

    content_type = sniff_type(payload, document.content_type, document.filename)
    if content_type is None:
        log.warning(
            "verification_rejected_type",
            declared=document.content_type,
            filename=document.filename,
            head=payload[:8].hex(),
        )
        raise AppError("Upload a photo or a PDF of the document").as_http()

    profile = _profile_for(session, artisan.id)

    extension = {
        "application/pdf": "pdf",
        "image/png": "png",
        "image/heic": "heic",
        "image/webp": "webp",
    }.get(content_type, "jpg")
    path = f"verification/{artisan.id}/identity.{extension}"

    try:
        await run_in_threadpool(
            supabase.upload,
            payload,
            path,
            content_type,
            DOCUMENT_BUCKET,
        )
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc

    # Store the object path, not a public URL. The reviewer's client signs it.
    profile.verification_document_url = path
    profile.is_verified = False
    # Where she works, which is what every state page and the ministry
    # dashboard group by. Without it her listings appear under no state at all.
    if state_code:
        profile.state_code = state_code[:4].upper()
    if craft:
        profile.craft = craft[:80]
    if district:
        profile.district = district[:80]
    if cluster:
        profile.cluster = cluster[:80]

    session.add(profile)
    session.commit()

    log.info("verification_submitted", artisan_id=str(artisan.id))
    return VerificationSubmitted(submitted=True, state="pending")
