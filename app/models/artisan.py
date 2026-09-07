"""Artisans, buyers and ministry officers. One table, separated by role."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import String
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utcnow


class Role(StrEnum):
    ARTISAN = "artisan"
    BUYER = "buyer"
    OFFICER = "officer"


class Scheme(StrEnum):
    """MoSJE categories. Drives the ministry dashboard breakdown."""

    SC = "scheduled_caste"
    OBC = "backward_classes"
    DNT = "denotified_nomadic"
    PWD = "persons_with_disabilities"
    SENIOR = "senior_citizen"
    NONE = "none"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)
    phone: str = Field(index=True, unique=True, max_length=20)
    name: str = Field(max_length=120)
    role: Role = Field(default=Role.ARTISAN, index=True, sa_type=String)
    password_hash: str | None = Field(default=None)
    preferred_language: str = Field(default="hi", max_length=8)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class ArtisanProfile(SQLModel, table=True):
    """Everything that only makes sense for a seller."""

    __tablename__ = "artisan_profiles"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)

    state_code: str = Field(max_length=4, index=True)
    district: str | None = Field(default=None, max_length=80)
    cluster: str | None = Field(default=None, max_length=80)
    craft: str | None = Field(default=None, max_length=80)

    # The link that makes a Craft Passport worth anything. Provenance is tied
    # to a scheme record rather than to a self declared shop name.
    scheme: Scheme = Field(default=Scheme.NONE, index=True, sa_type=String)
    beneficiary_id: str | None = Field(default=None, max_length=64, index=True)
    beneficiary_verified: bool = Field(default=False)

    # Baseline captured at intake, so income lift can be measured later.
    intake_monthly_income: int | None = Field(default=None)
    bio: str | None = Field(default=None)
    profile_image_path: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
