from __future__ import annotations
import math
import numpy as np
import pandas as pd
import pytest

from src.models.evaluate import mae, rmse, mape, r2


def test_mae_known_value():
    y = np.array([100.0, 200.0, 300.0])
    p = np.array([110.0, 190.0, 320.0])
    assert mae(y, p) == pytest.approx(40.0 / 3.0, rel=1e-6)


def test_rmse_known_value():
    y = np.array([100.0, 200.0, 300.0])
    p = np.array([110.0, 190.0, 320.0])
    expected = float(np.sqrt(np.mean((y - p) ** 2)))
    assert rmse(y, p) == pytest.approx(expected, rel=1e-6)


def test_mape_known_value():
    y = np.array([100.0, 200.0, 400.0])
    p = np.array([110.0, 220.0, 360.0])
    expected = float(np.mean(np.abs((y - p) / y))) * 100.0
    assert mape(y, p) == pytest.approx(expected, rel=1e-6)


def test_mape_skips_zero_targets():
    y = np.array([0.0, 200.0])
    p = np.array([10.0, 220.0])
    out = mape(y, p)
    assert math.isfinite(out)


def test_r2_perfect_and_imperfect():
    y = np.array([100.0, 200.0, 300.0, 400.0])
    assert r2(y, y.copy()) == pytest.approx(1.0, rel=1e-6)
    bad = np.array([200.0, 200.0, 200.0, 200.0])
    assert r2(y, bad) < 1.0
