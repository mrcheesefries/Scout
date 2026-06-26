"""
Indicator tests — §7 acceptance tests 1 and 4.

Test 1 (§7.1) is the most important: no lookahead bias in Donchian channels.
"""
import numpy as np
import pandas as pd
import pytest

from strategy.indicators import donchian_channels, atr, trend_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ohlcv(n: int = 100, high=None, low=None, close=None, volume=None) -> pd.DataFrame:
    dates = pd.date_range('2020-01-01', periods=n, freq='B')
    close = np.asarray(close if close is not None else np.ones(n) * 100.0)
    high = np.asarray(high if high is not None else close + 1.0)
    low = np.asarray(low if low is not None else close - 1.0)
    volume = np.asarray(volume if volume is not None else np.ones(n) * 1_000_000)
    return pd.DataFrame(
        {'open': close, 'high': high, 'low': low, 'close': close, 'volume': volume},
        index=dates,
    )


# ---------------------------------------------------------------------------
# §7.1 — THE CRITICAL TEST: no lookahead bias
# ---------------------------------------------------------------------------

def test_no_lookahead_donchian_20():
    """
    Bar N has an all-time high. upper_20 for bar N must NOT include bar N.
    If bar N is included, every bar would trivially be its own high — the scanner lies.
    """
    n = 60
    highs = np.ones(n) * 100.0
    lows = np.ones(n) * 99.0

    # Bar 58 (N-1) spikes to 200, bar 59 (N) spikes even higher to 300
    highs[58] = 200.0
    highs[59] = 300.0

    df = make_ohlcv(n=n, high=highs, low=lows, close=np.ones(n) * 100.0)
    result = donchian_channels(df)

    # upper_20 at bar 59 uses bars 39..58 (prior 20 bars, excluding 59)
    # max of those highs = 200.0 (bar 58 spike), NOT 300.0 (bar 59 itself)
    upper_at_n = result['upper_20'].iloc[59]
    assert upper_at_n == 200.0, (
        f"LOOKAHEAD BIAS: upper_20 at bar N is {upper_at_n}, "
        f"expected 200.0 (excluding current bar's high of 300.0)"
    )


def test_no_lookahead_donchian_lower():
    """lower_20 at bar N must not include bar N's low."""
    n = 60
    lows = np.ones(n) * 50.0
    highs = np.ones(n) * 51.0

    lows[58] = 10.0   # N-1: deep low
    lows[59] = 1.0    # N: even deeper

    df = make_ohlcv(n=n, high=highs, low=lows, close=np.ones(n) * 50.0)
    result = donchian_channels(df)

    lower_at_n = result['lower_20'].iloc[59]
    assert lower_at_n == 10.0, (
        f"LOOKAHEAD BIAS: lower_20 at bar N is {lower_at_n}, expected 10.0"
    )


def test_donchian_window_rolls_correctly():
    """The spike at bar 30 appears in upper_20 at bar 50 but not bar 51."""
    n = 80
    highs = np.ones(n) * 10.0
    lows = np.ones(n) * 5.0

    highs[30] = 20.0
    lows[30] = 1.0

    df = make_ohlcv(n=n, high=highs, low=lows, close=np.ones(n) * 7.0)
    result = donchian_channels(df)

    # upper_20 at bar 50 uses bars 30..49 — spike at 30 is included
    assert result['upper_20'].iloc[50] == 20.0
    # upper_20 at bar 51 uses bars 31..50 — spike at 30 dropped out
    assert result['upper_20'].iloc[51] == 10.0

    # lower_20 at bar 50 uses bars 30..49 — low spike at 30 included
    assert result['lower_20'].iloc[50] == 1.0
    # lower_20 at bar 51: spike gone
    assert result['lower_20'].iloc[51] == 5.0


# ---------------------------------------------------------------------------
# §7.4 — ATR stop math
# ---------------------------------------------------------------------------

def test_atr_constant_range():
    """Constant TR=10 every bar → Wilder ATR converges to exactly 10."""
    n = 30
    df = make_ohlcv(n=n, high=np.ones(n) * 105.0, low=np.ones(n) * 95.0, close=np.ones(n) * 100.0)
    result = atr(df, period=20)
    valid = result.dropna()

    assert len(valid) > 0
    np.testing.assert_allclose(valid.values, 10.0, rtol=1e-10)


def test_atr_known_values():
    """ATR with all TR=20 → ATR = 20.0 exactly after seed period."""
    n = 30
    df = make_ohlcv(n=n, high=np.ones(n) * 110.0, low=np.ones(n) * 90.0, close=np.ones(n) * 100.0)
    result = atr(df, period=20)

    atr_val = result.dropna().iloc[-1]
    assert atr_val == pytest.approx(20.0, rel=1e-10)

    # Stop math (§2.2)
    entry = 100.0
    assert entry - 2 * atr_val == pytest.approx(60.0)   # LONG stop
    assert entry + 2 * atr_val == pytest.approx(140.0)  # SHORT stop


def test_atr_wilder_seed_then_smooth():
    """
    Manual Wilder's smoothing verification.
    Bars 0..19: TR=4 → seed ATR=4.0
    Bar 20: TR=4 → ATR stays 4.0 (Wilder update with same value)
    Bar 21: TR=24 → ATR = (4*19 + 24)/20 = 5.0
    """
    n = 22
    highs = np.ones(n) * 102.0
    lows = np.ones(n) * 98.0
    closes = np.ones(n) * 100.0
    # Bar 21 (index 21): spike TR = max(24, 12, 12) = 24
    highs[21] = 112.0
    lows[21] = 88.0

    df = make_ohlcv(n=n, high=highs, low=lows, close=closes)
    result = atr(df, period=20)
    valid = result.dropna()

    # valid[0] = seed at index 19 = mean(TR[0..19]) = 4.0
    assert valid.iloc[0] == pytest.approx(4.0, rel=1e-10)
    # valid[1] = Wilder update at index 20 with TR[20]=4.0 → still 4.0
    assert valid.iloc[1] == pytest.approx(4.0, rel=1e-10)
    # valid[2] = Wilder update at index 21 with TR[21]=24.0 → (4*19+24)/20 = 5.0
    assert valid.iloc[2] == pytest.approx(5.0, rel=1e-10)


# ---------------------------------------------------------------------------
# Trend state
# ---------------------------------------------------------------------------

def test_trend_uptrend():
    """Steadily rising prices → uptrend at end."""
    n = 250
    closes = np.linspace(50, 200, n)
    df = make_ohlcv(n=n, close=closes)
    result = trend_state(df)
    assert result.iloc[-1] == 'uptrend'


def test_trend_downtrend():
    """Steadily falling prices → downtrend at end."""
    n = 250
    closes = np.linspace(200, 50, n)
    df = make_ohlcv(n=n, close=closes)
    result = trend_state(df)
    assert result.iloc[-1] == 'downtrend'


def test_trend_flat_no_trend():
    """Flat prices → price == SMA50 == SMA200 → no_trend."""
    n = 250
    df = make_ohlcv(n=n, close=np.ones(n) * 100.0)
    result = trend_state(df)
    assert result.iloc[-1] == 'no_trend'


def test_trend_requires_200_bars():
    """With fewer than 200 bars, SMA200 is NaN → no_trend (can't confirm uptrend)."""
    n = 100
    closes = np.linspace(50, 200, n)
    df = make_ohlcv(n=n, close=closes)
    result = trend_state(df)
    assert result.iloc[-1] == 'no_trend'
