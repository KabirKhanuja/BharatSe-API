"""Phone OTP sign in.

The OTP is stubbed for the prototype. What matters architecturally is that the
token carries the role, because the role is what decides whether this person
gets a storefront, a listing tool, or the ministry dashboard.
"""

from fastapi import APIRouter, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.errors import NotFoundError, UnauthorizedError
from app.core.security import create_access_token
from app.models.artisan import ArtisanProfile, Role, User
from app.schemas.auth import FirebaseSignIn, OtpRequest, OtpVerify, Token
from app.schemas.common import Message
from app.services.auth.firebase import verify_id_token

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


@router.post("/firebase", response_model=Token)
def firebase_sign_in(body: FirebaseSignIn, session: SessionDep) -> Token:
    """Exchange a Firebase ID token for one of ours.

    Firebase says who someone is. Postgres stays the source of truth for what
    they are, because role, verification state and everything they own live
    here and not in an identity provider.

    Matching is on the Firebase uid, falling back to email once so an account
    created by the phone OTP path is adopted rather than duplicated.
    """
    firebase_user = verify_id_token(body.id_token)

    user = session.exec(
        select(User).where(User.firebase_uid == firebase_user.uid)
    ).first()

    if user is None and firebase_user.email:
        user = session.exec(
            select(User).where(User.email == firebase_user.email)
        ).first()
        if user is not None:
            user.firebase_uid = firebase_user.uid

    if user is None and not body.create:
        # A restore, and we have never seen this person. Say so rather than
        # inventing an account with a guessed role.
        raise NotFoundError("No account for this sign in yet").as_http()

    created = user is None
    if created:
        user = User(
            firebase_uid=firebase_user.uid,
            email=firebase_user.email,
            name=body.name or firebase_user.name or "New user",
            # Only set at creation. See FirebaseSignIn.
            role=body.role,
        )
        session.add(user)
        session.flush()  # need the id before the profile references it

    # Keep the profile in step with the identity provider. Google may hand us a
    # name or an email we did not have on a previous sign in.
    if firebase_user.email and not user.email:
        user.email = firebase_user.email
    if firebase_user.name and user.name in ("", "New user"):
        user.name = firebase_user.name

    if user.role == Role.ARTISAN:
        # Create the seller profile immediately rather than on first document
        # upload. The ministry queue, the passport and the dashboard all join
        # through this row, and a seller with no profile is a row of nulls
        # everywhere downstream.
        profile = session.exec(
            select(ArtisanProfile).where(ArtisanProfile.user_id == user.id)
        ).first()
        if profile is None:
            session.add(ArtisanProfile(user_id=user.id, state_code="XX"))

    if not user.is_active:
        raise UnauthorizedError("This account is disabled").as_http()

    session.commit()
    session.refresh(user)

    return Token(
        access_token=create_access_token(str(user.id), user.role),
        role=user.role,
        user_id=str(user.id),
        name=user.name,
    )
