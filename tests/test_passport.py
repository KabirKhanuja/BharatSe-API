"""Craft Passport signing. Interop with the Dart client depends on these."""

from app.services.passport.signing import (
    _b64,
    decode_payload,
    generate_keypair,
    verify_passport,
)


def test_keys_are_raw_32_bytes():
    """Only raw encoding loads on the Dart side. A PEM blob will not."""
    private_hex, public_hex = generate_keypair()
    assert len(bytes.fromhex(private_hex)) == 32
    assert len(bytes.fromhex(public_hex)) == 32


def test_signature_round_trips():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    private = Ed25519PrivateKey.generate()
    public_hex = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())

    payload = b'{"pid":"abc","craft":"pashmina"}'
    signature = private.sign(payload)

    assert verify_passport(_b64(payload), _b64(signature), public_hex) is True


def test_tampered_payload_fails_verification():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    private = Ed25519PrivateKey.generate()
    public_hex = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    signature = private.sign(b'{"pid":"abc"}')
    assert verify_passport(_b64(b'{"pid":"xyz"}'), _b64(signature), public_hex) is False


def test_wrong_key_fails_verification():
    """An attacker shipping their own key must not verify. This is why the
    public key is pinned in the app and never read from the QR."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    real = Ed25519PrivateKey.generate()
    attacker = Ed25519PrivateKey.generate()
    attacker_public = attacker.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    signature = real.sign(b'{"pid":"abc"}')
    assert verify_passport(_b64(b'{"pid":"abc"}'), _b64(signature), attacker_public) is False


def test_payload_decodes_for_display():
    payload = b'{"craft":"pashmina","pid":"abc"}'
    assert decode_payload(_b64(payload))["craft"] == "pashmina"
