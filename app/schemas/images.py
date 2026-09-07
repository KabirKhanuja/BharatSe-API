import uuid

from pydantic import BaseModel


class EnhanceResponse(BaseModel):
    original_url: str
    enhanced_url: str | None

    # How the enhanced image was produced: "generative", "cutout" or "none".
    # The app can say so, and logs show how often the generative path was
    # actually reachable.
    method: str


class ListingImage(BaseModel):
    """One stored photo of a product.

    `position` 0 is the listing's primary image and is always the one the
    generative pass ran on, so a marketplace that reads only the first image
    still gets the catalogue quality one.
    """

    position: int
    original_url: str
    enhanced_url: str | None = None
    is_hero: bool = False


class ListingImagesResponse(BaseModel):
    """The result of preparing one product's photos.

    `enhanced_count` is 0 or 1 and never more. Generation is the only part of
    this service that costs real money per call, so the ceiling is a property
    of the response rather than something the caller is trusted to respect.
    """

    product_id: uuid.UUID
    client_id: str
    images: list[ListingImage]

    # What the listing should show. The enhanced image when there is one, and
    # the artisan's own photo when the model was unreachable, so a listing is
    # never imageless because an API was down.
    hero_url: str

    method: str
    enhanced_count: int
