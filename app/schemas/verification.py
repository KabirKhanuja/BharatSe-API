from pydantic import BaseModel


class PendingArtisanItem(BaseModel):
    id: str
    user_id: str
    name: str
    phone: str | None = None
    state: str
    district: str | None = None
    craft: str | None = None
    submitted_date: str
    verification_status: str  # "Pending", "Action Required", "Approved", "Rejected"
    is_verified: bool = False
    verification_document_url: str | None = None
    pehchan_id: str | None = "PHN-IN-284731"
    credentials_available: bool = True


class ArtisanVerificationDetail(BaseModel):
    id: str
    user_id: str
    name: str
    phone: str | None = None
    email: str | None = None
    state: str
    district: str | None = None
    cluster: str | None = None
    craft: str | None = None
    scheme: str | None = "none"
    beneficiary_id: str | None = None
    intake_monthly_income: int | None = None
    submitted_date: str
    is_verified: bool = False
    verification_document_url: str | None = None
    pehchan_id: str | None = "PHN-BR-284731"
    pehchan_status: str = "Pending Verification"
    workspace_verification_status: str = "Not Requested"
    product_count: int = 3
