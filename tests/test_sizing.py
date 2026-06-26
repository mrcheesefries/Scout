"""
Sizing tests — §7 acceptance test 5.
"""
import pytest
from strategy.sizing import position_size


def test_sizing_basic():
    """§7.5 — account 10,000, risk/share 5.00 → shares = 20, no off-by-one."""
    result = position_size(account_value=10_000, entry_ref=100.0, stop_ref=95.0)
    # risk_per_share = |100 - 95| = 5.0
    # shares = floor((10000 * 0.01) / 5.0) = floor(100 / 5) = 20
    assert result['shares'] == 20
    assert result['notional'] == pytest.approx(2000.0)
    assert result['risk_per_share'] == pytest.approx(5.0)


def test_sizing_floors_correctly():
    """Result must floor, never round up."""
    result = position_size(account_value=10_000, entry_ref=100.0, stop_ref=93.0)
    # risk = 7.0, max risk = 100, shares = floor(100/7) = floor(14.28) = 14
    assert result['shares'] == 14
    assert result['notional'] == pytest.approx(14 * 100.0)


def test_sizing_zero_account():
    """Zero account value → 0 shares."""
    result = position_size(account_value=0, entry_ref=100.0, stop_ref=90.0)
    assert result['shares'] == 0
    assert result['notional'] == 0.0


def test_sizing_stop_equals_entry():
    """Zero risk (stop == entry) → 0 shares, no division by zero."""
    result = position_size(account_value=10_000, entry_ref=100.0, stop_ref=100.0)
    assert result['shares'] == 0


def test_sizing_large_account():
    """Large account → correct scale."""
    result = position_size(account_value=100_000, entry_ref=50.0, stop_ref=40.0)
    # risk = 10, max_risk = 1000, shares = floor(1000/10) = 100
    assert result['shares'] == 100
    assert result['notional'] == pytest.approx(5000.0)


def test_sizing_short_stop_above_entry():
    """For a short, stop is above entry — |entry - stop| still computes correctly."""
    result = position_size(account_value=10_000, entry_ref=100.0, stop_ref=110.0)
    # risk = |100 - 110| = 10, shares = floor(100/10) = 10
    assert result['shares'] == 10
    assert result['risk_per_share'] == pytest.approx(10.0)
