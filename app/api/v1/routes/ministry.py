"""Ministry dashboard aggregates.

Officer only. Everything here is counts and averages across the programme, so
no route in this file ever returns an individual artisan's row.
"""

from fastapi import APIRouter
from sqlmodel import func, select

from app.api.deps import CurrentOfficer, SessionDep
from app.models.artisan import ArtisanProfile, Role, User
from app.models.passport import CraftPassport, PassportScan
from app.models.product import Product, ProductStatus

router = APIRouter(prefix="/ministry", tags=["ministry"])


@router.get("/overview")
def overview(officer: CurrentOfficer, session: SessionDep) -> dict:
    artisans = session.exec(
        select(func.count()).select_from(User).where(User.role == Role.ARTISAN)
    ).one()

    published = session.exec(
        select(func.count()).select_from(Product).where(Product.status == ProductStatus.PUBLISHED)
    ).one()

    issued = session.exec(select(func.count()).select_from(CraftPassport)).one()
    scans = session.exec(select(func.count()).select_from(PassportScan)).one()
    verified = session.exec(
        select(func.count()).select_from(PassportScan).where(PassportScan.verified)
    ).one()

    return {
        "registered_artisans": artisans,
        "published_listings": published,
        "passports": {"issued": issued, "scanned": scans, "verified": verified},
    }


@router.get("/by-scheme")
def by_scheme(officer: CurrentOfficer, session: SessionDep) -> list[dict]:
    rows = session.exec(
        select(ArtisanProfile.scheme, func.count())
        .select_from(ArtisanProfile)
        .group_by(ArtisanProfile.scheme)
    ).all()
    return [{"scheme": scheme, "beneficiaries": count} for scheme, count in rows]


@router.get("/by-state")
def by_state(officer: CurrentOfficer, session: SessionDep) -> list[dict]:
    rows = session.exec(
        select(ArtisanProfile.state_code, func.count())
        .select_from(ArtisanProfile)
        .group_by(ArtisanProfile.state_code)
    ).all()
    return [{"state_code": state, "artisans": count} for state, count in rows]
