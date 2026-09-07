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
        "https://x.supabase.co/storage/v1/object/public/product-assets/"
        "products/p1/original/abc.jpg"
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
