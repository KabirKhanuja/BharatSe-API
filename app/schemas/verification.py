from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PendingArtisanItem(BaseModel):
    id: str
    user_id: str
    name: str
    phone: Optional[str] = None
    state: str
    district: Optional[str] = None
    craft: Optional[str] = None
    submitted_date: str
    verification_status: str  # "Pending", "Action Required", "Approved", "Rejected"
    is_verified: bool = False
    verification_document_url: Optional[str] = None
    pehchan_id: Optional[str] = "PHN-IN-284731"
    credentials_available: bool = True

class ArtisanVerificationDetail(BaseModel):
    id: str
    user_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    state: str
    district: Optional[str] = None
    cluster: Optional[str] = None
    craft: Optional[str] = None
    scheme: Optional[str] = "none"
    beneficiary_id: Optional[str] = None
    intake_monthly_income: Optional[int] = None
    submitted_date: str
    is_verified: bool = False
    verification_document_url: Optional[str] = None
    pehchan_id: Optional[str] = "PHN-BR-284731"
    pehchan_status: str = "Pending Verification"
    workspace_verification_status: str = "Not Requested"
    product_count: int = 3
