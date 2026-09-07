from __future__ import annotations
import pytest

from src.pricing.policy import apply_outlier_guard


def test_apply_outlier_guard_widens_with_few_comparables():
    out = apply_outlier_guard(price=2500.0, market_median=2500.0, comparable_count=2)
    assert "single_seller_risk" in out.flags
    assert out.adjusted_price >= 2500.0


def test_apply_outlier_guard_no_op_with_enough_comparables():
    out = apply_outlier_guard(price=2500.0, market_median=2500.0, comparable_count=10)
    assert out.adjusted_price == 2500.0
    assert out.flags == []


def test_apply_outlier_guard_no_op_without_market_median():
    out = apply_outlier_guard(price=2500.0, market_median=None, comparable_count=2)
    assert out.adjusted_price == 2500.0
    assert out.flags == []


def test_apply_outlier_guard_threshold_is_five():
    out_at_four = apply_outlier_guard(price=2500.0, market_median=2500.0, comparable_count=4)
    out_at_five = apply_outlier_guard(price=2500.0, market_median=2500.0, comparable_count=5)
    assert "single_seller_risk" in out_at_four.flags
    assert out_at_five.flags == []
