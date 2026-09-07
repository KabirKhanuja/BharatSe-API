from __future__ import annotations
import pytest

from src.pricing.policy import (
    apply_insufficient_data,
    PolicyValidationError,
)


def test_apply_insufficient_data_returns_cost_floor_times_margin():
    out = apply_insufficient_data(price=0.0, cost_floor_value=2000.0, comparable_count=0)
    assert out.adjusted_price == 2000.0 * 1.5
    assert "insufficient_comparables" in out.flags


def test_apply_insufficient_data_above_floor():
    out = apply_insufficient_data(price=5000.0, cost_floor_value=2000.0, comparable_count=0)
    assert out.adjusted_price >= 2000.0
    assert out.adjusted_price == 3000.0


def test_apply_insufficient_data_no_op_with_data():
    out = apply_insufficient_data(price=2500.0, cost_floor_value=2000.0, comparable_count=10)
    assert out.adjusted_price == 2500.0
    assert out.flags == []


def test_apply_insufficient_data_rejects_margin_below_one():
    with pytest.raises(PolicyValidationError):
        apply_insufficient_data(price=2500.0, cost_floor_value=2000.0, comparable_count=0, margin=0.9)


def test_apply_insufficient_data_custom_margin_respected():
    out = apply_insufficient_data(price=0.0, cost_floor_value=1000.0, comparable_count=0, margin=2.0)
    assert out.adjusted_price == 2000.0
