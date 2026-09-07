from typing import Literal

from pydantic import BaseModel

VerificationState = Literal["not_submitted", "pending", "approved"]


class VerificationStatus(BaseModel):
    submitted: bool
    is_verified: bool

    # One field the app can switch on, rather than making it derive the state
    # from two booleans and get it wrong.
    state: VerificationState


class VerificationSubmitted(BaseModel):
    submitted: bool
    state: VerificationState
