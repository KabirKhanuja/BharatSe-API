from __future__ import annotations
import pytest

from src.pricing.policy import apply_market_sanity


def test_apply_market_sanity_within_band_no_flag():
    out = apply_market_sanity(price=2500.0, market_p10=2000.0, market_p90=3000.0)
    assert out.adjusted_price == 2500.0
    assert out.flags == []


def test_apply_market_sanity_clips_low():
    out = apply_market_sanity(price=1500.0, market_p10=2000.0, market_p90=3000.0)
    assert out.adjusted_price == 2000.0
    assert "market_sanity_clipped_low" in out.flags


def test_apply_market_sanity_clips_high():
    out = apply_market_sanity(price=5000.0, market_p10=2000.0, market_p90=3000.0)
    assert out.adjusted_price == 3000.0
    assert "market_sanity_clipped_high" in out.flags


def test_apply_market_sanity_at_boundary():
    out_low = apply_market_sanity(price=2000.0, market_p10=2000.0, market_p90=3000.0)
    out_high = apply_market_sanity(price=3000.0, market_p10=2000.0, market_p90=3000.0)
    assert out_low.adjusted_price == 2000.0
    assert out_high.adjusted_price == 3000.0


def test_apply_market_sanity_no_op_when_band_missing():
    out = apply_market_sanity(price=2500.0, market_p10=None, market_p90=None)
    assert out.adjusted_price == 2500.0
    assert out.flags == []
