"""Products, and the endpoint the phone's outbox drains into."""

import uuid

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentArtisan, SessionDep
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.product import Product, ProductStatus
from app.schemas.common import Page
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
    SyncBatch,
    SyncResult,
)
from app.services.pricing import PriceInput, suggest_price

router = APIRouter(prefix="/products", tags=["products"])
log = get_logger(__name__)


def _apply_pricing(product: Product) -> None:
    """Fill the band and the floor whenever the inputs are known."""
    if product.hours_of_work is None or product.material_cost is None:
        return

    suggestion = suggest_price(
        PriceInput(
            category=product.category or "other",
            material=product.material or "unknown",
            technique=product.technique or "unknown",
            state_code=product.state_code or "unknown",
            hours_of_work=product.hours_of_work,
            material_cost=product.material_cost,
            title=product.title_en or "",
            description=product.description_en or "",
        )
    )
    product.price_floor = suggestion.floor
    product.price_p10 = suggestion.p10
    product.price_p50 = suggestion.p50
    product.price_p90 = suggestion.p90

    # The guarantee, enforced server side and not only in the app. A price can
    # never be stored below what the maker's own labour is worth.
    if product.price is not None and product.price < suggestion.floor:
        product.price = suggestion.floor


@router.get("", response_model=Page[ProductOut])
def list_products(
    artisan: CurrentArtisan,
    session: SessionDep,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[ProductOut]:
    base = select(Product).where(Product.artisan_id == artisan.id)
    total = session.exec(
        select(func.count()).select_from(Product).where(Product.artisan_id == artisan.id)
    ).one()

    rows = session.exec(
        base.order_by(col(Product.created_at).desc()).limit(limit).offset(offset)
    ).all()

    return Page(
        items=[ProductOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ProductOut)
def create_product(body: ProductCreate, artisan: CurrentArtisan, session: SessionDep) -> ProductOut:
    existing = session.exec(select(Product).where(Product.client_id == body.client_id)).first()

    product = existing or Product(client_id=body.client_id, artisan_id=artisan.id)
    for field, value in body.model_dump(exclude_unset=True, exclude={"client_id"}).items():
        setattr(product, field, value)

    product.status = ProductStatus.READY
    _apply_pricing(product)

    session.add(product)
    session.commit()
    session.refresh(product)
    return ProductOut.model_validate(product)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, artisan: CurrentArtisan, session: SessionDep) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None or product.artisan_id != artisan.id:
        raise NotFoundError("No such product").as_http()
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    artisan: CurrentArtisan,
    session: SessionDep,
) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None or product.artisan_id != artisan.id:
        raise NotFoundError("No such product").as_http()

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    _apply_pricing(product)
    session.add(product)
    session.commit()
    session.refresh(product)
    return ProductOut.model_validate(product)


@router.post("/sync", response_model=SyncResult)
def sync(body: SyncBatch, artisan: CurrentArtisan, session: SessionDep) -> SyncResult:
    """Drain the phone's outbox.

    Upserts on client_id, so this is safe to retry. A dropped connection
    halfway through a batch costs a retry and never a duplicate.
    """
    created = updated = 0
    ids: dict[str, uuid.UUID] = {}

    for item in body.products:
        product = session.exec(select(Product).where(Product.client_id == item.client_id)).first()

        if product is None:
            product = Product(client_id=item.client_id, artisan_id=artisan.id)
            created += 1
        else:
            updated += 1

        for field, value in item.model_dump(exclude_unset=True, exclude={"client_id"}).items():
            setattr(product, field, value)

        product.status = ProductStatus.READY
        _apply_pricing(product)
        session.add(product)
        session.flush()
        ids[item.client_id] = product.id

    session.commit()
    log.info("outbox_drained", artisan_id=str(artisan.id), created=created, updated=updated)

    return SyncResult(accepted=len(body.products), created=created, updated=updated, ids=ids)
