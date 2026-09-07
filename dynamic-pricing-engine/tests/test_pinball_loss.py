from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

from src.models.evaluate import pinball_loss, mae


def test_pinball_loss_alpha_0_5_equals_mae():
    y = np.array([100.0, 200.0, 300.0, 400.0])
    p = np.array([110.0, 190.0, 320.0, 380.0])
    assert pinball_loss(y, p, alpha=0.5) == pytest.approx(mae(y, p), rel=1e-6)


def test_pinball_loss_zero_when_equal():
    y = np.array([100.0, 200.0, 300.0])
    p = np.array([100.0, 200.0, 300.0])
    assert pinball_loss(y, p, alpha=0.5) == 0.0
    assert pinball_loss(y, p, alpha=0.1) == 0.0
    assert pinball_loss(y, p, alpha=0.9) == 0.0


def test_pinball_loss_alpha_0_1_rewards_underprediction():
    y = np.array([200.0, 200.0])
    p_under = np.array([100.0, 100.0])
    p_over = np.array([300.0, 300.0])
    assert pinball_loss(y, p_under, alpha=0.1) < pinball_loss(y, p_over, alpha=0.1)


def test_pinball_loss_alpha_0_9_rewards_overprediction():
    y = np.array([200.0, 200.0])
    p_under = np.array([100.0, 100.0])
    p_over = np.array([300.0, 300.0])
    assert pinball_loss(y, p_over, alpha=0.9) < pinball_loss(y, p_under, alpha=0.9)
