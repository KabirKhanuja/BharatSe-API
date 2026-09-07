"""Shared dependencies."""

from typing import Annotated

from fastapi import Depends, Header
from sqlmodel import Session, select

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.artisan import Role, User

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token").as_http()

    payload = decode_access_token(authorization.split(" ", 1)[1])
    if payload is None:
        raise UnauthorizedError("Token is invalid or expired").as_http()

    user = session.exec(select(User).where(User.id == payload.get("sub"))).first()
    if user is None or not user.is_active:
        raise UnauthorizedError("User no longer exists").as_http()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: Role):
    """Route guard. The role comes from the session, so one codebase serves
    artisans, buyers and ministry officers without them seeing each other."""

    def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ForbiddenError(f"This endpoint is for {', '.join(allowed)}").as_http()
        return user

    return _guard


CurrentArtisan = Annotated[User, Depends(require_role(Role.ARTISAN))]
CurrentOfficer = Annotated[User, Depends(require_role(Role.OFFICER))]
