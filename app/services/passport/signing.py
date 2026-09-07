"""Craft Passport signing and verification.

Ed25519, raw 32 byte keys and 64 byte signatures, plain RFC 8032. The Dart side
verifies with cryptography_plus and interoperates because both implement the
same standard.

The thing that breaks these demos: Dart's jsonEncode and Python's json.dumps
differ in key order and spacing, so re-serialising the payload on the client to
verify it will fail even when the signature is correct. The QR therefore carries
the encoded BYTES that were signed, and the client verifies those exact bytes
and only decodes afterwards for display.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from app.core.config import settings
from app.core.errors import AppError


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def generate_keypair() -> tuple[str, str]:
    """Return (private_hex, public_hex). Only Raw encoding gives the 32 bytes
    the Dart side can load; a PEM blob will not."""
    private = Ed25519PrivateKey.generate()
    return (
        private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex(),
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
    )


@dataclass
class SignedPassport:
    payload_b64: str
    signature_b64: str
    public_key_hex: str

    @property
    def qr_content(self) -> str:
        """What actually goes in the QR: the signed bytes and the signature."""
        return f"{self.payload_b64}.{self.signature_b64}"


def sign_passport(
    product_id: str,
    artisan_id: str,
    beneficiary_id: str | None,
    craft: str,
    state_code: str,
    hours_of_work: float | None,
) -> SignedPassport:
    if not settings.PASSPORT_PRIVATE_KEY_HEX:
        raise AppError("PASSPORT_PRIVATE_KEY_HEX is not set. Run python scripts/generate_keys.py")

    payload = {
        "v": 1,
        "pid": product_id,
        "aid": artisan_id,
        "ben": beneficiary_id,
        "craft": craft,
        "state": state_code,
        "hours": hours_of_work,
        "iat": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    # Canonical form, so the bytes are reproducible on this side at least.
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(settings.PASSPORT_PRIVATE_KEY_HEX))
    signature = private.sign(raw)

    return SignedPassport(
        payload_b64=_b64(raw),
        signature_b64=_b64(signature),
        public_key_hex=settings.PASSPORT_PUBLIC_KEY_HEX,
    )


def verify_passport(payload_b64: str, signature_b64: str, public_key_hex: str) -> bool:
    """Verify the exact bytes that were signed.

    Note that cryptography's verify() returns None and raises on failure. It
    does not return a bool, so `if key.verify(...)` would accept everything.
    """
    try:
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public.verify(_unb64(signature_b64), _unb64(payload_b64))
    except (InvalidSignature, ValueError):
        return False
    return True


def decode_payload(payload_b64: str) -> dict:
    """For display only. Never re-encode this and verify against it."""
    return json.loads(_unb64(payload_b64))
