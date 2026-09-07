"""Phone OTP sign in.

The OTP is stubbed for the prototype. What matters architecturally is that the
token carries the role, because the role is what decides whether this person
gets a storefront, a listing tool, or the ministry dashboard.
"""

from fastapi import APIRouter, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token
from app.models.artisan import Role, User
from app.schemas.auth import OtpRequest, OtpVerify, Token
from app.schemas.common import Message

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_OTP = "123456"


@router.post("/otp/request", response_model=Message)
def request_otp(body: OtpRequest) -> Message:
    # TODO: wire an SMS gateway. Until then the demo code is fixed.
    return Message(message=f"OTP sent to {body.phone}")


@router.post("/otp/verify", response_model=Token)
def verify_otp(body: OtpVerify, session: SessionDep) -> Token:
    if body.code != DEMO_OTP:
        raise UnauthorizedError("Incorrect code").as_http()

    user = session.exec(select(User).where(User.phone == body.phone)).first()
    if user is None:
        # First sign in creates an artisan. Buyers and officers are created
        # deliberately, not by walking in through this door.
        user = User(phone=body.phone, name="New artisan", role=Role.ARTISAN)
        session.add(user)
        session.commit()
        session.refresh(user)

    return Token(
        access_token=create_access_token(str(user.id), user.role),
        role=user.role,
        user_id=str(user.id),
        name=user.name,
    )


@router.get("/me", status_code=status.HTTP_200_OK)
def me(user: CurrentUser) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
        "preferred_language": user.preferred_language,
    }
