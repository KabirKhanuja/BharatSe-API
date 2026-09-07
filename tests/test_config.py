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
