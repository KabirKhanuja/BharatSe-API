"""Pricing must survive the model being unavailable.

LightGBM's macOS wheel does not bundle libomp, so `import lightgbm` fails at
dlopen on a machine without it. That is a plausible state on a teammate's
laptop an hour before a demo, and it must not take the endpoint down.
"""

from unittest.mock import patch

from app.services.pricing.service import PriceInput, suggest_price

ITEM = PriceInput(
    category="textiles",
    material="silk",
    technique="handwoven",
    state_code="jk",
    hours_of_work=12,
    material_cost=800,
)


def _assert_usable(suggestion):
    assert suggestion.model_used is False
    assert suggestion.p10 >= suggestion.floor
    assert suggestion.p10 <= suggestion.p50 <= suggestion.p90
    assert suggestion.note


def test_falls_back_when_lightgbm_cannot_load_its_native_library():
    with patch(
        "app.services.pricing.service._model.predict",
        side_effect=OSError("libomp.dylib not found"),
    ):
        _assert_usable(suggest_price(ITEM))


def test_falls_back_when_lightgbm_is_not_installed():
    with patch(
        "app.services.pricing.service._model.predict",
        side_effect=ImportError("No module named lightgbm"),
    ):
        _assert_usable(suggest_price(ITEM))


def test_falls_back_when_no_model_file_has_been_trained():
    with patch(
        "app.services.pricing.service._model.predict",
        side_effect=FileNotFoundError("no model"),
    ):
        _assert_usable(suggest_price(ITEM))


def test_validate_price_rejects_below_floor():
    from app.core.errors import BelowWageFloorError
    from app.services.pricing.service import validate_price

    try:
        validate_price(price=100, material_cost=800, hours_of_work=12)
    except BelowWageFloorError as exc:
        assert "below the fair wage floor" in exc.message
    else:
        raise AssertionError("a price below the floor must be rejected")


def test_validate_price_accepts_at_or_above_floor():
    from app.services.pricing.floor import compute_floor
    from app.services.pricing.service import validate_price

    floor = compute_floor(800, 12).floor
    assert validate_price(floor, 800, 12) == floor
