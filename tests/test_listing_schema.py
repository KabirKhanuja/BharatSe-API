"""Validation of whatever the model hands back.

Neither Gemini nor Claude honours length or item count constraints declared in
a schema, so they are enforced in validators. These tests are what keeps that
true.
"""

import pytest
from pydantic import ValidationError

from app.services.ai.schema import GeneratedListing


def _listing(**overrides):
    base = dict(
        title_en="Handwoven silk scarf",
        title_hi="हाथ से बुना रेशमी दुपट्टा",
        description_en="A scarf.",
        description_hi="एक दुपट्टा।",
        tags=["silk", "scarf", "handmade"],
        materials=["silk"],
        category="textiles",
    )
    base.update(overrides)
    return GeneratedListing(**base)


def test_accepts_a_well_formed_listing():
    assert _listing().category == "textiles"


def test_long_titles_are_trimmed_on_a_word_boundary():
    listing = _listing(title_en="word " * 40)
    assert len(listing.title_en) <= 60
    assert not listing.title_en.endswith(" ")


def test_empty_title_is_rejected():
    with pytest.raises(ValidationError):
        _listing(title_en="   ")


def test_too_few_tags_is_rejected():
    with pytest.raises(ValidationError):
        _listing(tags=["silk"])


def test_tags_are_lowercased_and_deduplicated():
    listing = _listing(tags=["Silk", "silk", " SCARF ", "handmade"])
    assert listing.tags == ["silk", "scarf", "handmade"]


def test_tags_are_capped_at_eight():
    listing = _listing(tags=[f"tag{i}" for i in range(20)])
    assert len(listing.tags) == 8


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        _listing(category="spaceship")
