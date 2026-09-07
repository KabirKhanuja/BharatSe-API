"""Products and their generated listings."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import String
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utcnow


class ProductStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"  # created offline, not yet reached us
    PROCESSING = "processing"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)

    # Generated on the phone before the row ever reaches the server, so a
    # retried offline upload upserts instead of creating a duplicate.
    client_id: str = Field(index=True, unique=True, max_length=64)

    artisan_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: ProductStatus = Field(
        default=ProductStatus.DRAFT, index=True, sa_type=String
    )

    title_en: str | None = Field(default=None, max_length=160)
    title_hi: str | None = Field(default=None, max_length=160)
    description_en: str | None = Field(default=None)
    description_hi: str | None = Field(default=None)

    category: str | None = Field(default=None, max_length=60, index=True)
    material: str | None = Field(default=None, max_length=120)
    technique: str | None = Field(default=None, max_length=120)
    state_code: str | None = Field(default=None, max_length=4, index=True)

    # Commerce fields
    sku: str | None = Field(default=None, max_length=64)
    stock_quantity: int = Field(default=0)
    unit: str = Field(default="piece", max_length=20)
    minimum_order_quantity: int = Field(default=1)
    is_made_to_order: bool = Field(default=False)

    # Pricing inputs and outputs. hours is the artisan's own number and it sets
    # the floor, so it is stored rather than inferred.
    hours_of_work: float | None = Field(default=None)
    material_cost: int | None = Field(default=None)
    price_floor: int | None = Field(default=None)
    price_p10: int | None = Field(default=None)
    price_p50: int | None = Field(default=None)
    price_p90: int | None = Field(default=None)
    price: int | None = Field(default=None)

    # Provenance of the demo catalogue, so a seeded row can never be mistaken
    # for a real artisan's listing.
    source_name: str | None = Field(default=None, max_length=120)
    source_url: str | None = Field(default=None)
    source_license: str | None = Field(default=None, max_length=120)
    is_demo_data: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class ProductImage(SQLModel, table=True):
    __tablename__ = "product_images"

    id: uuid.UUID = Field(default_factory=new_id, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)

    original_url: str = Field(max_length=500)
    cutout_url: str | None = Field(default=None, max_length=500)
    enhanced_url: str | None = Field(default=None, max_length=500)
    position: int = Field(default=0)
    source_url: str | None = Field(default=None)
    attribution: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
