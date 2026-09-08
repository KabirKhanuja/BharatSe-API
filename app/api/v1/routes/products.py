"""Products, and the endpoint the phone's outbox drains into."""

import uuid

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentArtisan, SessionDep
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.artisan import ArtisanProfile
from app.models.product import Product, ProductImage, ProductStatus
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


def _status_for(session, artisan_id) -> ProductStatus:
    """Whether this artisan's listings go live or wait.

    A verified artisan publishes straight to the buyer catalogue. An unverified
    one can still list, and her work is held at `ready` until an officer
    approves her identity.

    This is what makes verification mean something. Without it, approval is a
    screen a judge is told about; with it, approval is the thing standing
    between a listing and a buyer.
    """
    profile = session.exec(
        select(ArtisanProfile).where(ArtisanProfile.user_id == artisan_id)
    ).first()

    return (
        ProductStatus.PUBLISHED
        if profile is not None and profile.is_verified
        else ProductStatus.READY
    )


def _inherit_location(session, artisan_id, product: Product) -> None:
    """Take the state from the artisan's profile when the listing has none.

    She is asked where she works once, during verification, rather than on
    every product. Everything in the buyer app groups by state, so a listing
    without one is invisible on the map and in every state page.
    """
    if product.state_code:
        return

    profile = session.exec(
        select(ArtisanProfile).where(ArtisanProfile.user_id == artisan_id)
    ).first()

    if profile is not None and profile.state_code and profile.state_code != "XX":
        product.state_code = profile.state_code


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
        items=_with_images(session, rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def _with_images(session, products: list[Product]) -> list[ProductOut]:
    """Attach each product's photographs in one query rather than N.

    The phone rebuilds an artisan's catalogue from this after a reinstall, and
    a grid of grey squares would read as broken even though the data is fine.
    Prefers the generated photograph over the raw one, matching the buyer
    catalogue, so the same listing does not look different on the two sides.
    """
    if not products:
        return []

    ids = [p.id for p in products]
    images = session.exec(
        select(ProductImage)
        .where(col(ProductImage.product_id).in_(ids))
        .order_by(col(ProductImage.position))
    ).all()

    by_product: dict[uuid.UUID, list[str]] = {}
    for image in images:
        url = image.enhanced_url or image.original_url
        if url:
            by_product.setdefault(image.product_id, []).append(url)

    out = []
    for product in products:
        item = ProductOut.model_validate(product)
        item.image_urls = by_product.get(product.id, [])
        out.append(item)
    return out


@router.post("", response_model=ProductOut)
def create_product(body: ProductCreate, artisan: CurrentArtisan, session: SessionDep) -> ProductOut:
    existing = session.exec(select(Product).where(Product.client_id == body.client_id)).first()

    product = existing or Product(client_id=body.client_id, artisan_id=artisan.id)
    for field, value in body.model_dump(exclude_unset=True, exclude={"client_id"}).items():
        setattr(product, field, value)

    product.status = _status_for(session, artisan.id)
    _inherit_location(session, artisan.id, product)
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

        product.status = _status_for(session, artisan.id)
        _inherit_location(session, artisan.id, product)
        _apply_pricing(product)
        session.add(product)
        session.flush()
        ids[item.client_id] = product.id

    session.commit()
    log.info("outbox_drained", artisan_id=str(artisan.id), created=created, updated=updated)

    return SyncResult(accepted=len(body.products), created=created, updated=updated, ids=ids)
