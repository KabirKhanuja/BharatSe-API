"""Firebase token verification.

These are the checks that stop someone signing in as anybody. The audience one
in particular: without it, a token minted in an attacker's own Firebase project
would be accepted as one of ours.
"""

import time

import pytest
from jose import jwt

from app.core.errors import UnauthorizedError
from app.services.auth import firebase


@pytest.fixture
def keypair():
    from datetime import UTC, datetime, timedelta

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509 import CertificateBuilder, Name, NameAttribute
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = Name([NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (
        CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    pem_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode()
    return pem_key, pem_cert


@pytest.fixture(autouse=True)
def project(monkeypatch):
    monkeypatch.setattr(firebase.settings, "FIREBASE_PROJECT_ID", "bharatse-test")
    yield


def _token(pem_key, *, aud="bharatse-test", iss=None, sub="uid-123", exp_delta=3600):
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "aud": aud,
            "iss": iss or f"{firebase.ISSUER_PREFIX}bharatse-test",
            "iat": now,
            "exp": now + exp_delta,
            "email": "artisan@example.com",
            "name": "Meena",
        },
        pem_key,
        algorithm="RS256",
        headers={"kid": "testkey"},
    )


def _serve(monkeypatch, pem_cert):
    monkeypatch.setattr(firebase, "_fetch_certs", lambda force=False: {"testkey": pem_cert})


def test_accepts_a_token_from_our_project(keypair, monkeypatch):
    pem_key, pem_cert = keypair
    _serve(monkeypatch, pem_cert)

    user = firebase.verify_id_token(_token(pem_key))
    assert user.uid == "uid-123"
    assert user.email == "artisan@example.com"
    assert user.name == "Meena"


def test_rejects_a_token_minted_for_another_project(keypair, monkeypatch):
    """The attack this whole function exists to stop."""
    pem_key, pem_cert = keypair
    _serve(monkeypatch, pem_cert)

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key, aud="someone-elses-project"))


def test_rejects_a_wrong_issuer(keypair, monkeypatch):
    pem_key, pem_cert = keypair
    _serve(monkeypatch, pem_cert)

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key, iss="https://evil.example.com"))


def test_rejects_an_expired_token(keypair, monkeypatch):
    pem_key, pem_cert = keypair
    _serve(monkeypatch, pem_cert)

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key, exp_delta=-60))


def test_rejects_a_token_signed_by_someone_else(keypair, monkeypatch):
    """A valid looking token signed with a key that is not Google's."""
    pem_key, _ = keypair
    _, other_cert = _fresh_keypair()
    _serve(monkeypatch, other_cert)

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key))


def test_rejects_an_unknown_key_id(keypair, monkeypatch):
    pem_key, _ = keypair
    monkeypatch.setattr(firebase, "_fetch_certs", lambda force=False: {"otherkey": "x"})

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key))


def test_rejects_rubbish():
    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token("not-a-token")


def test_refuses_to_run_without_a_project_id(keypair, monkeypatch):
    pem_key, pem_cert = keypair
    _serve(monkeypatch, pem_cert)
    monkeypatch.setattr(firebase.settings, "FIREBASE_PROJECT_ID", "")

    with pytest.raises(UnauthorizedError):
        firebase.verify_id_token(_token(pem_key))


def _fresh_keypair():
    from datetime import UTC, datetime, timedelta

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509 import CertificateBuilder, Name, NameAttribute
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = Name([NameAttribute(NameOID.COMMON_NAME, "other")])
    cert = (
        CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(2)
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return (
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        cert.public_bytes(serialization.Encoding.PEM).decode(),
    )
