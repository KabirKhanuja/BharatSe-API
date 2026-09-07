from __future__ import annotations
import pytest

from src.pricing.confidence import (
    ReliabilityInputs,
    compute_reliability_score,
)


def _inputs(**overrides) -> ReliabilityInputs:
    base = dict(
        comparable_count=20,
        feature_completeness=0.9,
        data_recency_days=7,
        market_dispersion=0.1,
        interval_width_ratio=0.2,
    )
    base.update(overrides)
    return ReliabilityInputs(**base)


def test_reliability_score_is_integer_in_range():
    score = compute_reliability_score(_inputs())
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_reliability_higher_with_more_comparables():
    low = compute_reliability_score(_inputs(comparable_count=0))
    mid = compute_reliability_score(_inputs(comparable_count=10))
    high = compute_reliability_score(_inputs(comparable_count=50))
    assert low < mid < high


def test_reliability_lower_with_wider_interval():
    narrow = compute_reliability_score(_inputs(interval_width_ratio=0.1))
    wide = compute_reliability_score(_inputs(interval_width_ratio=0.6))
    assert wide < narrow


def test_reliability_lower_with_higher_dispersion():
    tight = compute_reliability_score(_inputs(market_dispersion=0.05))
    loose = compute_reliability_score(_inputs(market_dispersion=0.5))
    assert loose < tight


def test_reliability_lower_with_missing_features():
    full = compute_reliability_score(_inputs(feature_completeness=1.0))
    half = compute_reliability_score(_inputs(feature_completeness=0.5))
    assert half < full


def test_reliability_higher_with_more_recent_data():
    stale = compute_reliability_score(_inputs(data_recency_days=120))
    fresh = compute_reliability_score(_inputs(data_recency_days=3))
    assert fresh > stale


def test_reliability_saturates_at_50_comparables():
    a = compute_reliability_score(_inputs(comparable_count=50))
    b = compute_reliability_score(_inputs(comparable_count=200))
    assert a == b
