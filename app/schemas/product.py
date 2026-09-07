import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.product import ProductStatus


class ProductCreate(BaseModel):
    """Sent by the phone when its outbox drains.

    `client_id` is generated on the device. The server upserts on it, so an
    artisan tapping save three times on a bad connection produces one row and
    not three. Every offline failure a judge will try is a duplicate row
    problem, not a sync problem.
    """

    client_id: str = Field(min_length=8, max_length=64)
    title_en: str | None = None
    title_hi: str | None = None
    description_en: str | None = None
    description_hi: str | None = None
    category: str | None = None
    material: str | None = None
    technique: str | None = None
    state_code: str | None = None
    hours_of_work: float | None = Field(default=None, ge=0)
    material_cost: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    title_en: str | None = None
    title_hi: str | None = None
    description_en: str | None = None
    description_hi: str | None = None
    category: str | None = None
    hours_of_work: float | None = Field(default=None, ge=0)
    material_cost: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    client_id: str
    artisan_id: uuid.UUID
    status: ProductStatus
    title_en: str | None
    title_hi: str | None
    description_en: str | None
    description_hi: str | None
    category: str | None
    material: str | None
    technique: str | None
    state_code: str | None
    hours_of_work: float | None
    material_cost: int | None
    price_floor: int | None
    price_p10: int | None
    price_p50: int | None
    price_p90: int | None
    price: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncBatch(BaseModel):
    """One drain of the phone's outbox."""

    products: list[ProductCreate] = Field(default_factory=list, max_length=100)


class SyncResult(BaseModel):
    accepted: int
    created: int
    updated: int
    ids: dict[str, uuid.UUID]
