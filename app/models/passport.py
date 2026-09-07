"""Craft Passport. A signed provenance record attached to a physical object."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import new_id, utcnow


class CraftPassport(SQLModel, table=True):
    __tablename__ = "craft_passports"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True, unique=True)
    artisan_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    # The exact bytes that were signed, base64url encoded. Verification reads
    # these back rather than re-serialising the payload, because JSON key order
    # differs between the Dart and Python encoders and a re-serialised payload
    # will not match the signature.
    payload_b64: str = Field(max_length=2000)
    signature_b64: str = Field(max_length=200)
    public_key_hex: str = Field(max_length=64)

    scan_count: int = Field(default=0)
    last_scanned_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class PassportScan(SQLModel, table=True):
    """One row per scan, so the ministry can report verification rates."""

    __tablename__ = "passport_scans"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)
    passport_id: uuid.UUID = Field(foreign_key="craft_passports.id", index=True)
    verified: bool = Field(default=False)
    scanned_at: datetime = Field(default_factory=utcnow, nullable=False)
    country_code: str | None = Field(default=None, max_length=4)
    state_code: str | None = Field(default=None, max_length=4)
    referrer: str | None = Field(default=None)
