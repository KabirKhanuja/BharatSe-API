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
