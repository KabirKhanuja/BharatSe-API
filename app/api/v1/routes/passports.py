"""Craft Passport issuance and verification."""

import uuid

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import CurrentArtisan, SessionDep
from app.core.errors import AppError, NotFoundError
from app.models.artisan import ArtisanProfile
from app.models.passport import CraftPassport, PassportScan
from app.models.product import Product
from app.schemas.passport import PassportOut, VerifyRequest, VerifyResponse
from app.services.passport.signing import (
    decode_payload,
    sign_passport,
    verify_passport,
)

router = APIRouter(prefix="/passports", tags=["passports"])


@router.post("/{product_id}/issue", response_model=PassportOut)
def issue(product_id: uuid.UUID, artisan: CurrentArtisan, session: SessionDep) -> PassportOut:
    product = session.get(Product, product_id)
    if product is None or product.artisan_id != artisan.id:
        raise NotFoundError("No such product").as_http()

    profile = session.exec(
        select(ArtisanProfile).where(ArtisanProfile.user_id == artisan.id)
    ).first()

    try:
        signed = sign_passport(
            product_id=str(product.id),
            artisan_id=str(artisan.id),
            beneficiary_id=profile.beneficiary_id if profile else None,
            craft=product.technique or product.category or "handicraft",
            state_code=product.state_code or (profile.state_code if profile else "unknown"),
            hours_of_work=product.hours_of_work,
        )
    except AppError as exc:
        raise exc.as_http() from exc

    existing = session.exec(
        select(CraftPassport).where(CraftPassport.product_id == product.id)
    ).first()

    passport = existing or CraftPassport(product_id=product.id, artisan_id=artisan.id)
    passport.payload_b64 = signed.payload_b64
    passport.signature_b64 = signed.signature_b64
    passport.public_key_hex = signed.public_key_hex

    session.add(passport)
    session.commit()

    return PassportOut(
        product_id=str(product.id),
        qr_content=signed.qr_content,
        payload_b64=signed.payload_b64,
        signature_b64=signed.signature_b64,
        public_key_hex=signed.public_key_hex,
    )


@router.post("/verify", response_model=VerifyResponse)
def verify(body: VerifyRequest, session: SessionDep) -> VerifyResponse:
    """Public. A buyer scanning a tag has no account.

    Verification is done against the exact bytes carried in the QR. The payload
    is only decoded afterwards, for display.
    """
    from app.core.config import settings

    key = body.public_key_hex or settings.PASSPORT_PUBLIC_KEY_HEX
    if not key:
        raise AppError("No public key available to verify against").as_http()

    ok = verify_passport(body.payload_b64, body.signature_b64, key)

    passport = session.exec(
        select(CraftPassport).where(CraftPassport.payload_b64 == body.payload_b64)
    ).first()
    if passport is not None:
        passport.scan_count += 1
        session.add(passport)
        session.add(PassportScan(passport_id=passport.id, verified=ok))
        session.commit()

    return VerifyResponse(
        verified=ok,
        payload=decode_payload(body.payload_b64) if ok else None,
        message="Provenance verified" if ok else "This tag could not be verified",
    )
