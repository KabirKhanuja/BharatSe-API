from pydantic import BaseModel


class PassportOut(BaseModel):
    product_id: str
    qr_content: str
    payload_b64: str
    signature_b64: str
    public_key_hex: str


class VerifyRequest(BaseModel):
    payload_b64: str
    signature_b64: str
    public_key_hex: str | None = None


class VerifyResponse(BaseModel):
    verified: bool
    payload: dict | None = None
    message: str
