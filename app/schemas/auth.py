from pydantic import BaseModel, Field

from app.models.artisan import Role


class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=15)


class OtpVerify(BaseModel):
    phone: str = Field(min_length=10, max_length=15)
    code: str = Field(min_length=4, max_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str
    name: str


class FirebaseSignIn(BaseModel):
    """What the app sends after Firebase has authenticated someone.

    `role` is only honoured the first time. Someone who signed up as a buyer
    cannot become a seller by sending a different value on their next sign in,
    because that would walk straight around identity verification.
    """

    id_token: str = Field(min_length=20)
    role: Role = Role.BUYER
    name: str = ""

    # False when the app is silently restoring a session on launch rather than
    # someone actively signing up. Without this, a restored Firebase session
    # creates an account before the person has chosen whether they are here to
    # buy or to sell, and role is fixed at creation.
    create: bool = True
