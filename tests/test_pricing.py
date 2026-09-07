"""The pricing rules, which are the part of this service we make claims about."""

import pytest

from app.services.pricing.floor import OVERHEAD_RATE, compute_floor
from app.services.pricing.model import empirical_coverage, pinball_loss
from app.services.pricing.service import PriceInput, suggest_price


def test_floor_is_materials_plus_labour_plus_overhead():
    breakdown = compute_floor(material_cost=380, hours_of_work=7, wage_per_hour=60)

    assert breakdown.labour_cost == 420
    assert breakdown.overhead == round((380 + 420) * OVERHEAD_RATE)
    assert breakdown.floor == 380 + 420 + breakdown.overhead


def test_more_hours_raises_the_floor():
    low = compute_floor(380, 7)
    high = compute_floor(380, 27)
    assert high.floor > low.floor


def test_floor_rejects_negative_inputs():
    with pytest.raises(ValueError):
        compute_floor(-1, 5)
    with pytest.raises(ValueError):
        compute_floor(100, -5)


def test_suggestion_is_never_below_the_floor():
    """The one guarantee this service makes."""
    item = PriceInput(
        category="textiles",
        material="silk",
        technique="handwoven",
        state_code="jk",
        hours_of_work=96,
        material_cost=1200,
    )
    suggestion = suggest_price(item)

    assert suggestion.p10 >= suggestion.floor
    assert suggestion.p50 >= suggestion.p10
    assert suggestion.p90 >= suggestion.p50


def test_band_is_ordered_for_a_cheap_item_too():
    item = PriceInput(
        category="pottery",
        material="clay",
        technique="wheel",
        state_code="rj",
        hours_of_work=2,
        material_cost=60,
    )
    s = suggest_price(item)
    assert s.p10 <= s.p50 <= s.p90


def test_falls_back_rather_than_failing_when_no_model_is_trained():
    """An artisan on a bad connection gets an answer, not an error."""
    item = PriceInput(
        category="woodwork",
        material="teak",
        technique="carved",
        state_code="ka",
        hours_of_work=10,
        material_cost=500,
    )
    s = suggest_price(item)

    assert s.p50 > 0
    assert s.note


def test_pinball_loss_is_zero_on_a_perfect_prediction():
    import numpy as np

    truth = np.array([100.0, 200.0, 300.0])
    assert pinball_loss(truth, truth, 0.5) == 0.0


def test_coverage_counts_only_values_inside_the_band():
    import numpy as np

    truth = np.array([100.0, 200.0, 300.0])
    low = np.array([90.0, 190.0, 500.0])
    high = np.array([110.0, 210.0, 600.0])

    assert empirical_coverage(truth, low, high) == pytest.approx(2 / 3)
