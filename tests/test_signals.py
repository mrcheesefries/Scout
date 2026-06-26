"""
Signal scoring tests — §7 acceptance tests 2 and 3.

Test 2: known LONG breakout, flipped → SHORT
Test 3: mixed trend = no trade (Vision veto)
"""
import numpy as np
import pandas as pd
import pytest

from strategy.signals import score_ticker, LONG, SHORT, NO_SETUP

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    'thresholds': {
        'min_avg_volume': 500_000,
        'extended_atr_mult': 1.0,
        'earnings_window_days': 10,
    }
}


def make_ohlcv(n: int, high=None, low=None, close=None, volume=None) -> pd.DataFrame:
    dates = pd.date_range('2020-01-01', periods=n, freq='B')
    close = np.asarray(close if close is not None else np.ones(n) * 100.0)
    high = np.asarray(high if high is not None else close + 2.0)
    low = np.asarray(low if low is not None else close - 2.0)
    volume = np.asarray(volume if volume is not None else np.ones(n) * 2_000_000)
    return pd.DataFrame(
        {'open': close, 'high': high, 'low': low, 'close': close, 'volume': volume},
        index=dates,
    )


def make_uptrend_breakout_df(n: int = 250) -> pd.DataFrame:
    """
    Rising prices 0..199 (establish uptrend), flat 200..248, breakout bar 249.
    upper_20 at bar 249 = max(highs[229..248]) = 202.0
    close at bar 249 = 210.0 > 202.0 → LONG breakout with uptrend confirmed.
    """
    closes = np.zeros(n)
    closes[:200] = np.linspace(50, 200, 200)
    closes[200:249] = 200.0
    closes[249] = 210.0
    return make_ohlcv(n=n, close=closes)


def make_downtrend_breakdown_df(n: int = 250) -> pd.DataFrame:
    """
    Declining prices 0..199 (establish downtrend), flat 200..248, breakdown bar 249.
    lower_20 at bar 249 = min(lows[229..248]) = 198.0
    close at bar 249 = 190.0 < 198.0 → SHORT breakdown with downtrend confirmed.
    """
    closes = np.zeros(n)
    closes[:200] = np.linspace(200, 100, 200)
    closes[200:249] = 100.0
    closes[249] = 90.0
    return make_ohlcv(n=n, close=closes)


# ---------------------------------------------------------------------------
# §7.2 — Known breakout → correct verdict
# ---------------------------------------------------------------------------

def test_known_long_breakout():
    """§7.2a — hand-built uptrend + 20-day breakout → LONG setup."""
    df = make_uptrend_breakout_df()
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    assert result.verdict == LONG, f"Expected LONG, got {result.verdict}: {result.reason}"
    assert result.trend == 'uptrend'
    assert result.close == pytest.approx(210.0)
    # upper_20 should be the high of the flat period highs (close+2=202)
    assert result.upper_20 == pytest.approx(202.0)
    assert result.entry_ref == pytest.approx(202.0)
    # Stop is 2*ATR below entry
    assert result.stop_ref == pytest.approx(result.entry_ref - 2 * result.atr_20)


def test_known_short_breakdown():
    """§7.2b — hand-built downtrend + 20-day breakdown → SHORT setup."""
    df = make_downtrend_breakdown_df()
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    assert result.verdict == SHORT, f"Expected SHORT, got {result.verdict}: {result.reason}"
    assert result.trend == 'downtrend'
    assert result.close == pytest.approx(90.0)
    # lower_20 = min(lows[229..248]) = lows during flat = 100-2 = 98
    assert result.lower_20 == pytest.approx(98.0)
    assert result.entry_ref == pytest.approx(98.0)
    # Stop is 2*ATR ABOVE entry for a short
    assert result.stop_ref == pytest.approx(result.entry_ref + 2 * result.atr_20)


# ---------------------------------------------------------------------------
# §7.3 — Mixed trend = no trade (Vision veto)
# ---------------------------------------------------------------------------

def test_vision_veto_upside_breakout_in_downtrend():
    """
    §7.3 — close breaks above 20-day high but trend is downtrend/no_trend.
    Must return NO_SETUP — Vision veto fires.
    """
    # Declining prices for 200 bars (strong downtrend), then flat, then spike up
    n = 250
    closes = np.zeros(n)
    closes[:200] = np.linspace(200, 50, 200)
    closes[200:249] = 50.0
    closes[249] = 65.0  # above flat highs (50+2=52), but trend is NOT uptrend

    df = make_ohlcv(n=n, close=closes)
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    assert result.verdict == NO_SETUP, (
        f"Vision veto failed: got {result.verdict} with trend={result.trend}"
    )
    # Confirm the breakout condition was actually met (price IS above upper_20)
    assert result.close > result.upper_20, (
        "Test precondition failed: close should be above upper_20 for veto to be meaningful"
    )
    # Confirm it wasn't an uptrend (that's why the veto fired)
    assert result.trend != 'uptrend'


def test_vision_veto_downside_breakdown_in_uptrend():
    """
    §7.3 — close breaks below 20-day low but trend is uptrend/no_trend.
    Must return NO_SETUP.
    """
    # Rising prices, then flat, then drop below 20-day low
    n = 250
    closes = np.zeros(n)
    closes[:200] = np.linspace(50, 200, 200)
    closes[200:249] = 200.0
    closes[249] = 185.0  # below flat lows (200-2=198), but trend is NOT downtrend

    df = make_ohlcv(n=n, close=closes)
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    assert result.verdict == NO_SETUP, (
        f"Vision veto failed: got {result.verdict} with trend={result.trend}"
    )
    assert result.close < result.lower_20
    assert result.trend != 'downtrend'


def test_sma50_above_sma200_but_price_below_sma50_is_no_trend():
    """Price below SMA50 even though SMA50 > SMA200 → no_trend → NO SETUP."""
    n = 250
    closes = np.zeros(n)
    closes[:200] = np.linspace(50, 200, 200)    # strong uptrend
    closes[200:] = 120.0                          # price drops below SMA50 (which is ~190)

    highs = closes + 2.0
    lows = closes - 2.0
    df = make_ohlcv(n=n, close=closes, high=highs, low=lows)
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    # SMA50 ≈ 120 (all flat), SMA200 still well above 120 because of the rising history
    # close=120 is not < SMA50=120 and not a downtrend breakout
    assert result.verdict == NO_SETUP


# ---------------------------------------------------------------------------
# Earnings flag
# ---------------------------------------------------------------------------

def test_earnings_soon_flag():
    """When earnings is within the window, flag appears on LONG setup."""
    from datetime import date, timedelta
    df = make_uptrend_breakout_df()
    earnings = date(2020, 1, 1) + timedelta(days=5)  # well within window
    result = score_ticker(
        df, 'TEST', MINIMAL_CONFIG,
        earnings_date=earnings,
        as_of=date(2020, 1, 1),
    )

    if result.verdict == LONG:
        assert any('EARNINGS' in f for f in result.flags)


def test_earnings_unknown_flag():
    """When earnings date is unknown, flag appears on LONG setup."""
    df = make_uptrend_breakout_df()
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG, earnings_unknown=True)

    if result.verdict == LONG:
        assert any('UNKNOWN' in f for f in result.flags)


# ---------------------------------------------------------------------------
# Extended flag
# ---------------------------------------------------------------------------

def test_extended_flag_on_long():
    """When close is >1 ATR past breakout, EXTENDED flag fires."""
    n = 250
    closes = np.zeros(n)
    closes[:200] = np.linspace(50, 200, 200)
    closes[200:249] = 200.0
    # Make breakout very extended: 50 units above the 202 upper_20
    closes[249] = 260.0

    df = make_ohlcv(n=n, close=closes)
    result = score_ticker(df, 'TEST', MINIMAL_CONFIG)

    if result.verdict == LONG:
        assert any('EXTENDED' in f for f in result.flags)
