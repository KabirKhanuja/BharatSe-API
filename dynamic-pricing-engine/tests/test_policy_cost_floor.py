from __future__ import annotations
import pytest

from src.pricing.policy import apply_cost_floor, PolicyResult


def test_apply_cost_floor_returns_max():
    out = apply_cost_floor(price=1000.0, cost_floor_value=1500.0)
    assert isinstance(out, PolicyResult)
    assert out.adjusted_price == 1500.0


def test_apply_cost_floor_lifts_below_floor():
    out = apply_cost_floor(price=2000.0, cost_floor_value=2500.0)
    assert out.adjusted_price == 2500.0


def test_apply_cost_floor_at_floor_is_no_op():
    out = apply_cost_floor(price=1500.0, cost_floor_value=1500.0)
    assert out.adjusted_price == 1500.0
    assert out.flags == []


def test_apply_cost_floor_above_floor_unchanged():
    out = apply_cost_floor(price=2000.0, cost_floor_value=1500.0)
    assert out.adjusted_price == 2000.0
    assert out.flags == []


def test_apply_cost_floor_flags_lift():
    out = apply_cost_floor(price=1000.0, cost_floor_value=1500.0)
    assert "cost_floor_lift" in out.flags
