from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    health,
    images,
    listings,
    ministry,
    passports,
    pricing,
    products,
    search,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(listings.router)
api_router.include_router(images.router)
api_router.include_router(pricing.router)
api_router.include_router(passports.router)
api_router.include_router(search.router)
api_router.include_router(ministry.router)
