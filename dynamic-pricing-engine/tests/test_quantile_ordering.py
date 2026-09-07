from __future__ import annotations
import math
import numpy as np
import pandas as pd
import pytest

from src.models.evaluate import enforce_quantile_order


def test_enforce_quantile_order_returns_sorted():
    p10 = np.array([100.0, 200.0, 300.0])
    p50 = np.array([50.0, 250.0, 250.0])
    p90 = np.array([400.0, 100.0, 200.0])
    s10, s50, s90 = enforce_quantile_order(p10, p50, p90)
    assert (s10 <= s50).all()
    assert (s50 <= s90).all()


def test_enforce_quantile_order_is_idempotent():
    p10 = np.array([100.0, 200.0])
    p50 = np.array([300.0, 100.0])
    p90 = np.array([400.0, 50.0])
    s10, s50, s90 = enforce_quantile_order(p10, p50, p90)
    t10, t50, t90 = enforce_quantile_order(s10, s50, s90)
    np.testing.assert_array_equal(s10, t10)
    np.testing.assert_array_equal(s50, t50)
    np.testing.assert_array_equal(s90, t90)


def test_enforce_quantile_order_handles_nan():
    p10 = np.array([100.0, np.nan])
    p50 = np.array([150.0, 150.0])
    p90 = np.array([200.0, np.nan])
    s10, s50, s90 = enforce_quantile_order(p10, p50, p90)
    assert not np.isnan(s10).any()
    assert not np.isnan(s50).any()
    assert not np.isnan(s90).any()


def test_enforce_quantile_order_is_pure():
    p10 = np.array([100.0, 200.0])
    p50 = np.array([150.0, 150.0])
    p90 = np.array([200.0, 100.0])
    a = enforce_quantile_order(p10, p50, p90)
    b = enforce_quantile_order(p10, p50, p90)
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)
