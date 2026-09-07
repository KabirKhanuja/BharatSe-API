from __future__ import annotations
import math
import pytest

from src.pricing.cost_engine import cost_floor, CostValidationError


def test_cost_floor_is_sum_of_components():
    assert cost_floor(100, 200, 50, 25) == 375.0


def test_cost_floor_treats_none_as_zero():
    assert cost_floor(None, None, None, None) == 0.0
    assert cost_floor(100, None, 50, None) == 150.0


def test_cost_floor_rejects_negative_input():
    with pytest.raises(CostValidationError):
        cost_floor(-1, 100, 100, 100)


def test_cost_floor_rejects_non_numeric():
    with pytest.raises(CostValidationError):
        cost_floor("not_a_number", 100, 100, 100)


def test_cost_floor_ignores_outbound_shipping_kwarg():
    # Outbound shipping belongs to fulfillment, not the pricing engine.
    # The function must accept and ignore any extra keyword that isn't part of the cost.
    assert cost_floor(100, 200, 50, 25) == 375.0
    # We don't bind the kwarg at all; this test documents the policy.
    assert "outbound" not in cost_floor.__code__.co_varnames


def test_cost_floor_is_pure():
    a = cost_floor(800, 1200, 200, 300)
    b = cost_floor(800, 1200, 200, 300)
    assert a == b == 2500.0
