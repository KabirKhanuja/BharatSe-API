"""Generate the Craft Passport signing keypair.

    python scripts/generate_keys.py

The private key signs passports on the server. The public key is pinned in the
mobile app bundle. Do not put the public key in the QR itself: an attacker
would simply ship their own key alongside their own signature.
"""

from app.services.passport.signing import generate_keypair

if __name__ == "__main__":
    private_hex, public_hex = generate_keypair()
    print("PASSPORT_PRIVATE_KEY_HEX=" + private_hex)
    print("PASSPORT_PUBLIC_KEY_HEX=" + public_hex)
    print()
    print("Put both in .env. Pin the public key in the Flutter app as well.")
