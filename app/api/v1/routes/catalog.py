"""Public product catalogue."""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import SessionDep
from app.core.errors import NotFoundError
from app.models.artisan import User
from app.models.product import Product, ProductImage, ProductStatus

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _product_json(
    product: Product,
    artisan: User,
    images: Sequence[ProductImage],
) -> dict[str, Any]:
    """Convert a product and its related data into frontend JSON."""

    primary_image = None

    for image in images:
        if image.enhanced_url:
            primary_image = image.enhanced_url
            break

    if primary_image is None and images:
        primary_image = images[0].original_url

    return {
        "id": str(product.id),
        "title_en": product.title_en,
        "title_hi": product.title_hi,
        "description_en": product.description_en,
        "description_hi": product.description_hi,
        "category": product.category,
        "material": product.material,
        "technique": product.technique,
        "state_code": product.state_code,
        "sku": product.sku,
        "price": product.price,
        "price_floor": product.price_floor,
        "price_p10": product.price_p10,
        "price_p50": product.price_p50,
        "price_p90": product.price_p90,
        "stock_quantity": product.stock_quantity,
        "unit": product.unit,
        "minimum_order_quantity": product.minimum_order_quantity,
        "is_made_to_order": product.is_made_to_order,
        "status": product.status,
        "artisan": {
            "id": str(artisan.id),
            "name": artisan.name,
        },
        "primary_image_url": primary_image,
        "images": [
            {
                "id": str(image.id),
                "position": image.position,
                "original_url": image.original_url,
                "cutout_url": image.cutout_url,
                "enhanced_url": image.enhanced_url,
            }
            for image in images
        ],
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


@router.get("/products")
def list_catalog_products(
    session: SessionDep,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return all published products for the buyer catalogue."""

    total = session.exec(
        select(func.count())
        .select_from(Product)
        .where(Product.status == ProductStatus.PUBLISHED)
    ).one()

    rows = session.exec(
        select(Product, User)
        .join(User, Product.artisan_id == User.id)
        .where(Product.status == ProductStatus.PUBLISHED)
        .order_by(col(Product.created_at).desc())
        .limit(limit)
        .offset(offset)
    ).all()

    product_ids = [product.id for product, _ in rows]

    images_by_product: dict[uuid.UUID, list[ProductImage]] = defaultdict(list)

    if product_ids:
        images = session.exec(
            select(ProductImage)
            .where(col(ProductImage.product_id).in_(product_ids))
            .order_by(col(ProductImage.position))
        ).all()

        for image in images:
            images_by_product[image.product_id].append(image)

    items = [
        _product_json(
            product,
            artisan,
            images_by_product.get(product.id, []),
        )
        for product, artisan in rows
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/products/{product_id}")
def get_catalog_product(
    product_id: uuid.UUID,
    session: SessionDep,
):
    """Return one published product by ID."""

    row = session.exec(
        select(Product, User)
        .join(User, Product.artisan_id == User.id)
        .where(
            Product.id == product_id,
            Product.status == ProductStatus.PUBLISHED,
        )
    ).first()

    if row is None:
        raise NotFoundError("Product not found").as_http()

    product, artisan = row

    images = session.exec(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(col(ProductImage.position))
    ).all()

    return _product_json(product, artisan, images)