"""Image studio.

Two paths, and the choice between them is deliberate.

The primary path is generative: Gemini redraws the object on a clean ground.
Nothing is subtracted, so there is no matte to get wrong on a frayed silk edge
or a wicker rim, and the lighting is corrected in the same pass.

The fallback is rembg plus OpenCV. It is worse on edges but it runs without a
network round trip and without a paid API, which matters if the venue wifi
turns out to be what venue wifi usually is.

Everything that generates or cuts out runs in a worker thread. Those calls are
synchronous and take tens of seconds, and awaiting them directly on the event
loop would stall every other request in the process for the duration.
"""

import uuid

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select

from app.api.deps import CurrentArtisan, SessionDep
from app.core.errors import AppError, NotFoundError, ProviderUnavailableError
from app.core.logging import get_logger
from app.models.artisan import User
from app.models.product import Product, ProductImage, ProductStatus
from app.schemas.images import EnhanceResponse, ListingImage, ListingImagesResponse
from app.services.images.background import remove_background
from app.services.images.enhance import auto_correct, compose_on_canvas
from app.services.images.generate import enhance as generate_enhanced
from app.services.storage import supabase

router = APIRouter(prefix="/images", tags=["images"])
log = get_logger(__name__)

MAX_IMAGE_BYTES = 12 * 1024 * 1024

# An artisan may attach several photos to a listing. Generation runs on exactly
# one of them, whatever the count.
#
# Both numbers are enforced here rather than in the app. A cap that lives only
# in the client is not a cap: this endpoint takes a bearer token and an
# arbitrary number of files, and image generation is the one call in this
# service billed per invocation. The app's own limit is there to make the rule
# visible, not to enforce it.
MAX_LISTING_IMAGES = 4
MAX_GENERATIONS_PER_LISTING = 1



def resolve_hero(enhance_index: int, count: int) -> int:
    """Which photo the model runs on.

    Out of range is a client bug, not a reason to reject an upload the artisan
    already waited through. Fall back to the first photo.
    """
    if count <= 0:
        return 0
    return enhance_index if 0 <= enhance_index < count else 0


def hero_order(count: int, hero: int) -> list[int]:
    """Positions for the stored rows, hero first.

    A consumer that reads only the primary image of a listing gets the enhanced
    one, without having to know this pipeline exists.
    """
    return [hero] + [i for i in range(count) if i != hero]


async def _read(upload: UploadFile) -> bytes:
    payload = await upload.read()
    if not payload:
        raise AppError("Empty image upload").as_http()
    if len(payload) > MAX_IMAGE_BYTES:
        raise AppError("Image is too large").as_http()
    return payload


async def _generate_or_cut(
    payload: bytes,
    label: str,
    mime_type: str,
    folder: str,
) -> tuple[str | None, str]:
    """One catalogue image, by whichever path is reachable.

    Returns the stored URL and how it was made. Never raises for a provider
    being down: an artisan who cannot reach Gemini should still end up with a
    listing, and the caller decides what to show.
    """
    try:
        rendered = await run_in_threadpool(generate_enhanced, payload, label, mime_type)
        url = await run_in_threadpool(
            supabase.upload,
            rendered,
            supabase.product_image_path(folder, "enhanced", "png"),
            "image/png",
        )
        return url, "generative"
    except ProviderUnavailableError as exc:
        # Fall back rather than failing. A usable cutout beats an error while
        # an artisan waits.
        log.warning("generative_enhance_failed", error=exc.message)

    try:
        corrected = await run_in_threadpool(auto_correct, payload)
        cut = await run_in_threadpool(remove_background, corrected)
        composed = await run_in_threadpool(compose_on_canvas, cut, "square")
        url = await run_in_threadpool(
            supabase.upload,
            composed,
            supabase.product_image_path(folder, "enhanced", "jpg"),
            "image/jpeg",
        )
        return url, "cutout"
    except ProviderUnavailableError as exc:
        log.warning("cutout_enhance_failed", error=exc.message)

    return None, "none"


def _draft_for(session: Session, artisan: User, client_id: str) -> Product:
    """The product row these photos belong to, created if this is the first call.

    Keyed on `client_id`, which the phone generates before anything reaches the
    network, exactly as `POST /products/sync` does. That is what lets photos be
    uploaded before the artisan has finished recording her voice note: whichever
    of the two arrives first creates the row and the other one fills in its half.
    Neither has to know about the other, and a retry of either is an upsert.
    """
    product = session.exec(select(Product).where(Product.client_id == client_id)).first()

    if product is None:
        product = Product(
            client_id=client_id,
            artisan_id=artisan.id,
            status=ProductStatus.DRAFT,
        )
        session.add(product)
        session.flush()
        return product

    # A client_id is a uuid from the device, so a collision across accounts is
    # not something that happens by accident. Refuse it as a not-found rather
    # than letting one artisan attach photos to another's listing.
    if product.artisan_id != artisan.id:
        raise NotFoundError("No such product").as_http()

    return product


@router.post("/listing", response_model=ListingImagesResponse)
async def listing_images(
    artisan: CurrentArtisan,
    session: SessionDep,
    images: list[UploadFile] = File(...),
    client_id: str = Form(...),
    label: str = Form(default=""),
    enhance_index: int = Form(default=0),
) -> ListingImagesResponse:
    """Every photo of one product, uploaded together, one of them enhanced.

    The artisan's originals are all kept. That is not sentimentality: the
    before and after is the feature, and a buyer disputing what they were shown
    should be answerable from the photograph that was actually taken.

    `enhance_index` picks which photo gets the model, so the artisan chooses her
    best shot rather than the pipeline assuming it was the first one.
    """
    if not images:
        raise AppError("At least one photo is required").as_http()
    if len(images) > MAX_LISTING_IMAGES:
        raise AppError(
            f"At most {MAX_LISTING_IMAGES} photos per listing"
        ).as_http()

    payloads = [await _read(upload) for upload in images]

    hero = resolve_hero(enhance_index, len(payloads))

    product = _draft_for(session, artisan, client_id)
    folder = str(product.id)

    originals: list[str] = []
    # strict: payloads is built one per upload, so a length mismatch is a bug
    # rather than something to silently truncate a photo over.
    for upload, payload in zip(images, payloads, strict=True):
        originals.append(
            await run_in_threadpool(
                supabase.upload,
                payload,
                supabase.product_image_path(folder, "original", "jpg"),
                upload.content_type or "image/jpeg",
            )
        )

    # The single generation. Not in the loop, and there is no path through this
    # function that reaches it twice.
    enhanced_url, method = await _generate_or_cut(
        payloads[hero],
        label or (product.title_en or ""),
        images[hero].content_type or "image/jpeg",
        folder,
    )

    # Replace rather than append. This endpoint is retried on a flaky connection
    # and an artisan may redo her photos, and neither should leave orphan rows
    # pointing at images no longer in the listing.
    for stale in session.exec(
        select(ProductImage).where(ProductImage.product_id == product.id)
    ).all():
        session.delete(stale)

    order = hero_order(len(originals), hero)

    out: list[ListingImage] = []
    for position, index in enumerate(order):
        is_hero = index == hero
        session.add(
            ProductImage(
                product_id=product.id,
                original_url=originals[index],
                enhanced_url=enhanced_url if is_hero else None,
                position=position,
            )
        )
        out.append(
            ListingImage(
                position=position,
                original_url=originals[index],
                enhanced_url=enhanced_url if is_hero else None,
                is_hero=is_hero,
            )
        )

    session.commit()

    log.info(
        "listing_images_prepared",
        artisan_id=str(artisan.id),
        product_id=str(product.id),
        photos=len(originals),
        method=method,
    )

    return ListingImagesResponse(
        product_id=product.id,
        client_id=client_id,
        images=out,
        hero_url=enhanced_url or originals[hero],
        method=method,
        enhanced_count=1 if enhanced_url else 0,
    )


@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_image(
    artisan: CurrentArtisan,
    session: SessionDep,
    image: UploadFile = File(...),
    label: str = Form(default=""),
    product_id: str = Form(default=""),
) -> EnhanceResponse:
    """One photo in, catalogue image out, both stored.

    Kept for callers that hold a real product id already and want to add a
    single image to it. The listing flow uses `/images/listing` instead.
    """
    payload = await _read(image)

    product: Product | None = None
    if product_id:
        try:
            product = session.get(Product, uuid.UUID(product_id))
        except ValueError:
            raise AppError("product_id is not a valid id").as_http() from None
        if product is None or product.artisan_id != artisan.id:
            raise NotFoundError("No such product").as_http()

    folder = product_id or f"drafts/{artisan.id}"
    original_url = await run_in_threadpool(
        supabase.upload,
        payload,
        supabase.product_image_path(folder, "original", "jpg"),
        image.content_type or "image/jpeg",
    )

    enhanced_url, method = await _generate_or_cut(
        payload,
        label or (product.title_en if product else "") or "",
        image.content_type or "image/jpeg",
        folder,
    )

    if product is not None:
        position = len(
            session.exec(
                select(ProductImage).where(ProductImage.product_id == product.id)
            ).all()
        )
        session.add(
            ProductImage(
                product_id=product.id,
                original_url=original_url,
                enhanced_url=enhanced_url,
                position=position,
            )
        )
        session.commit()

    return EnhanceResponse(
        original_url=original_url,
        enhanced_url=enhanced_url,
        method=method,
    )


@router.post("/cutout")
async def cutout(artisan: CurrentArtisan, image: UploadFile = File(...)) -> Response:
    """Cutout only, returned as bytes. Used when the caller wants the mask
    rather than a stored asset."""
    payload = await _read(image)
    try:
        result = await run_in_threadpool(remove_background, payload)
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc
    return Response(content=result, media_type="image/png")


@router.post("/studio")
async def studio(
    artisan: CurrentArtisan,
    image: UploadFile = File(...),
    aspect: str = Form(default="square"),
) -> Response:
    """The local pass: correct, cut out, and place on a clean canvas."""
    payload = await _read(image)
    try:
        corrected = await run_in_threadpool(auto_correct, payload)
        cut = await run_in_threadpool(remove_background, corrected)
        composed = await run_in_threadpool(compose_on_canvas, cut, aspect)
    except ProviderUnavailableError as exc:
        raise exc.as_http() from exc
    return Response(content=composed, media_type="image/jpeg")
