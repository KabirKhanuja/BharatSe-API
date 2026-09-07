from pydantic import BaseModel

from app.services.ai.schema import GeneratedListing


class ListingResponse(BaseModel):
    listing: GeneratedListing
    provider: str
