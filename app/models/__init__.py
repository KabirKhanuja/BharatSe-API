"""Importing this package registers every table with SQLModel metadata.

Alembic autogenerate reads that metadata, so a model missing from here is a
model that silently never gets a migration.
"""

from app.models.artisan import ArtisanProfile, Role, Scheme, User
from app.models.passport import CraftPassport, PassportScan
from app.models.product import Product, ProductImage, ProductStatus

__all__ = [
    "ArtisanProfile",
    "CraftPassport",
    "PassportScan",
    "Product",
    "ProductImage",
    "ProductStatus",
    "Role",
    "Scheme",
    "User",
]
