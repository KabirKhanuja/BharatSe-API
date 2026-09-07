"""Verify Firebase ID tokens.

Done against Google's published certificates rather than with the Admin SDK.
That avoids storing a service account key, which is a credential that can do
anything in the project, and avoids a large dependency for one function.

What is checked, and why each one matters:
  signature   the token was minted by Google and not by the caller
  aud         it was minted for OUR project, not some other Firebase app
  iss         the same thing from the other direction
  exp         it has not expired
  sub         it identifies a user

Skipping `aud` is the classic mistake. Without it anyone can spin up their own
Firebase project, sign in there, and present that token to us as anybody.
"""

from __future__ import annotations

import time

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger

log = get_logger(__name__)

CERT_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/"
    "securetoken@system.gserviceaccount.com"
)
ISSUER_PREFIX = "https://securetoken.google.com/"

_certs: dict[str, str] = {}
_certs_fetched_at: float = 0.0

# Google rotates these roughly daily. An hour is well inside that and keeps us
# from fetching on every sign in.
_CERT_TTL = 3600


class FirebaseUser:
    def __init__(
        self,
        uid: str,
        email: str | None = None,
        name: str | None = None,
        picture: str | None = None,
    ) -> None:
        self.uid = uid
        self.email = email
        self.name = name
        self.picture = picture


def _fetch_certs(force: bool = False) -> dict[str, str]:
    global _certs, _certs_fetched_at

    fresh = time.time() - _certs_fetched_at < _CERT_TTL
    if _certs and fresh and not force:
        return _certs

    try:
        response = httpx.get(CERT_URL, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        if _certs:
            # Serve stale rather than locking everyone out over a network blip.
            log.warning("firebase_cert_refresh_failed", error=str(exc))
            return _certs
        raise UnauthorizedError("Could not reach Google to verify the sign in") from exc

    _certs = response.json()
    _certs_fetched_at = time.time()
    return _certs


def verify_id_token(token: str) -> FirebaseUser:
    if not settings.FIREBASE_PROJECT_ID:
        raise UnauthorizedError("FIREBASE_PROJECT_ID is not configured")

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise UnauthorizedError("Malformed sign in token") from exc

    kid = header.get("kid")
    if not kid:
        raise UnauthorizedError("Sign in token has no key id")

    certs = _fetch_certs()
    if kid not in certs:
        # Key rotated since we last looked. Refetch once before giving up.
        certs = _fetch_certs(force=True)

    certificate = certs.get(kid)
    if certificate is None:
        raise UnauthorizedError("Sign in token was signed with an unknown key")

    try:
        claims = jwt.decode(
            token,
            certificate,
            algorithms=["RS256"],
            audience=settings.FIREBASE_PROJECT_ID,
            issuer=f"{ISSUER_PREFIX}{settings.FIREBASE_PROJECT_ID}",
        )
    except JWTError as exc:
        raise UnauthorizedError(f"Sign in token rejected: {exc}") from exc

    uid = claims.get("sub") or claims.get("user_id")
    if not uid:
        raise UnauthorizedError("Sign in token identifies no user")

    return FirebaseUser(
        uid=uid,
        email=claims.get("email"),
        name=claims.get("name"),
        picture=claims.get("picture"),
    )
