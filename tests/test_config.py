"""Settings parsing.

CORS_ORIGINS is a list read from a plain comma separated env value.
pydantic-settings tries to JSON decode list fields from .env, so without
NoDecode this raises at import time and the whole service fails to boot. That
would surface on first deploy and nowhere earlier, so it is pinned here.
"""

from app.core.config import Settings


def test_comma_separated_origins_parse_into_a_list():
    settings = Settings(CORS_ORIGINS="http://a.test, http://b.test")
    assert settings.CORS_ORIGINS == ["http://a.test", "http://b.test"]


def test_empty_origins_are_dropped():
    settings = Settings(CORS_ORIGINS="http://a.test,,  ,")
    assert settings.CORS_ORIGINS == ["http://a.test"]


def test_a_real_list_still_works():
    settings = Settings(CORS_ORIGINS=["http://a.test"])
    assert settings.CORS_ORIGINS == ["http://a.test"]


def test_rembg_model_is_never_the_paid_default():
    """rembg's own default is BRIA RMBG, which needs a paid commercial
    agreement. Shipping that on a government problem statement is not
    something we want one forgotten argument away."""
    assert Settings().REMBG_MODEL == "isnet-general-use"


def test_listing_key_falls_back_to_the_main_key():
    settings = Settings(GEMINI_API_KEY="paid", GEMINI_LISTING_API_KEY="")
    assert settings.listing_api_key == "paid"


def test_a_dedicated_listing_key_wins():
    """So the voice path can sit on a free tier project while images bill."""
    settings = Settings(GEMINI_API_KEY="paid", GEMINI_LISTING_API_KEY="free")
    assert settings.listing_api_key == "free"


def test_no_keys_at_all_reads_as_unset():
    assert Settings(GEMINI_API_KEY="", GEMINI_LISTING_API_KEY="").listing_api_key == ""
