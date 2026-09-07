"""The image studio path."""

import base64

import pytest

from app.api.v1.routes.images import (
    MAX_GENERATIONS_PER_LISTING,
    MAX_LISTING_IMAGES,
    hero_order,
    resolve_hero,
)
from app.core.errors import ProviderUnavailableError
from app.services.images.generate import decode_data_uri
from app.services.images.studio_prompt import render
from app.services.storage import supabase


def test_decodes_a_base64_data_uri():
    payload = b"\x89PNG\r\n\x1a\n"
    uri = "data:image/png;base64," + base64.b64encode(payload).decode()
    assert decode_data_uri(uri) == payload


def test_rejects_something_that_is_not_an_image():
    with pytest.raises(ProviderUnavailableError):
        decode_data_uri("I cannot create that image.")


def test_prompt_keeps_the_three_load_bearing_instructions():
    prompt = render("blue pottery vase")

    assert "blue pottery vase" in prompt
    # Without this the model quietly restyles the object.
    assert "Preserve exactly" in prompt
    # Artisans photograph their work while holding it.
    assert "no hands" in prompt
    # The one instruction specific to handmade goods.
    assert "irregularities are the product" in prompt


def test_prompt_survives_a_missing_label():
    assert "handmade craft object" in render("")


def test_storage_paths_do_not_collide():
    a = supabase.product_image_path("p1", "original")
    b = supabase.product_image_path("p1", "original")
    assert a != b, "two uploads at once must not overwrite each other"
    assert a.startswith("products/p1/original/")


def test_public_url_is_built_from_the_configured_project(monkeypatch):
    monkeypatch.setattr(supabase.settings, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(supabase.settings, "SUPABASE_BUCKET", "product-assets")

    url = supabase.public_url("products/p1/original/abc.jpg")
    assert url == (
        "https://x.supabase.co/storage/v1/object/public/product-assets/products/p1/original/abc.jpg"
    )


def test_upload_refuses_when_the_service_key_is_missing(monkeypatch):
    monkeypatch.setattr(supabase.settings, "SUPABASE_SERVICE_KEY", "")
    with pytest.raises(ProviderUnavailableError):
        supabase.upload(b"x", "products/p/original/a.jpg")


# ---------------------------------------------------------------- listing flow


def test_hero_is_the_photo_the_artisan_chose():
    assert resolve_hero(2, 4) == 2


def test_an_out_of_range_choice_falls_back_to_the_first_photo():
    # A client bug must not cost the artisan the upload she already waited for.
    assert resolve_hero(9, 3) == 0
    assert resolve_hero(-1, 3) == 0
    assert resolve_hero(0, 0) == 0


def test_the_hero_is_stored_first():
    # A marketplace that reads only the primary image must get the enhanced one.
    assert hero_order(4, 2)[0] == 2


def test_every_photo_is_stored_exactly_once():
    for count in range(1, MAX_LISTING_IMAGES + 1):
        for hero in range(count):
            order = hero_order(count, hero)
            assert sorted(order) == list(range(count)), (count, hero)


def test_generation_is_capped_at_one_per_listing():
    # The number that keeps this endpoint from turning four photos into four
    # billed image generations.
    assert MAX_GENERATIONS_PER_LISTING == 1


def test_the_photo_cap_is_enforced_on_the_server():
    # The app has its own limit, but the app is not what protects the bill.
    assert MAX_LISTING_IMAGES == 4


def test_listing_route_is_published_and_needs_a_token():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    assert "/api/v1/images/listing" in client.get("/api/v1/openapi.json").json()["paths"]
    assert client.post("/api/v1/images/listing").status_code == 401


class TestDocumentSniffing:
    """A client-supplied content type is a label, not evidence.

    Flutter's MultipartFile sends application/octet-stream for everything, so
    trusting the header rejected every genuine document an artisan uploaded.
    """

    def _sniff(self, *args, **kwargs):
        from app.api.v1.routes.verification import sniff_type

        return sniff_type(*args, **kwargs)

    def test_recognises_a_jpeg_by_its_bytes(self):
        assert (
            self._sniff(b"\xff\xd8\xff\xe0rest", "application/octet-stream", None) == "image/jpeg"
        )

    def test_recognises_a_png_by_its_bytes(self):
        assert (
            self._sniff(b"\x89PNG\r\n\x1a\nrest", "application/octet-stream", None) == "image/png"
        )

    def test_recognises_a_pdf_by_its_bytes(self):
        assert self._sniff(b"%PDF-1.7 rest", "application/octet-stream", None) == "application/pdf"

    def test_recognises_heic_at_its_offset(self):
        # HEIC's marker sits at byte 4, not byte 0. iPhone photos arrive as this.
        payload = b"\x00\x00\x00\x18ftypheic" + b"rest"
        assert self._sniff(payload, "application/octet-stream", None) == "image/heic"

    def test_falls_back_to_the_filename_when_bytes_are_unknown(self):
        assert self._sniff(b"unknown", "application/octet-stream", "scan.png") == "image/png"

    def test_rejects_something_that_is_not_a_document(self):
        assert self._sniff(b"just some text", "application/octet-stream", "notes.txt") is None

    def test_bytes_win_over_a_lying_header(self):
        # A PDF declared as a JPEG is stored as a PDF, not mislabelled.
        assert self._sniff(b"%PDF-1.7", "image/jpeg", "x.jpg") == "application/pdf"

    def test_a_webp_needs_both_riff_and_webp_markers(self):
        assert (
            self._sniff(b"RIFF\x00\x00\x00\x00WEBP", "application/octet-stream", None)
            == "image/webp"
        )
        # RIFF alone is a wav or avi, not an image.
        assert self._sniff(b"RIFF\x00\x00\x00\x00WAVE", "application/octet-stream", None) is None


class TestVerificationDocumentUrls:
    """Identity documents are private, so the reviewer needs a signed URL.

    Getting this wrong fails in one of two bad ways: a broken image in the
    review queue, or an Aadhaar scan on a permanently public URL.
    """

    def _format(self, raw):
        from app.api.v1.routes.ministry import format_document_url

        return format_document_url(raw)

    def test_a_full_url_is_passed_through(self):
        url = "https://x.supabase.co/storage/v1/object/public/a/b.png"
        assert self._format(url) == url

    def test_a_bare_path_is_signed(self, monkeypatch):
        from app.api.v1.routes import ministry

        seen = {}

        def fake_sign(path, bucket=None, expires_in=3600):
            seen["path"] = path
            seen["bucket"] = bucket
            return "https://signed.example/doc?token=abc"

        monkeypatch.setattr(ministry.supabase, "signed_url", fake_sign)

        assert self._format("verification/uid/identity.jpg").startswith("https://signed")
        assert seen["path"] == "verification/uid/identity.jpg"
        assert seen["bucket"] == "verification-documents"

    def test_missing_document_shows_the_specimen(self):
        from app.api.v1.routes.ministry import SAMPLE_AADHAAR_DOC

        assert self._format(None) == SAMPLE_AADHAAR_DOC
        assert self._format("") == SAMPLE_AADHAAR_DOC

    def test_signing_failure_does_not_take_the_queue_down(self, monkeypatch):
        from app.api.v1.routes import ministry

        monkeypatch.setattr(ministry.supabase, "signed_url", lambda *a, **k: None)
        # Falls back rather than raising: a reviewer sees a broken panel, not a 500.
        assert self._format("verification/uid/identity.jpg").startswith("http")
