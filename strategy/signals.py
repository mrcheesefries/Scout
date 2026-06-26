"""
Signal scoring — pure function, no I/O.

Applies the Templar Code rules to compute LONG / SHORT / NO_SETUP
for a single ticker's OHLCV DataFrame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from strategy.indicators import donchian_channels, atr as compute_atr, trend_state

LONG = 'LONG'
SHORT = 'SHORT'
NO_SETUP = 'NO_SETUP'


@dataclass
class SignalResult:
    ticker: str
    verdict: str            # LONG | SHORT | NO_SETUP
    close: float
    upper_20: float
    lower_20: float
    upper_55: float
    lower_55: float
    trail_high_10: float
    trail_low_10: float
    atr_20: float
    trend: str              # uptrend | downtrend | no_trend
    entry_ref: Optional[float] = None
    stop_ref: Optional[float] = None
    trail_ref: Optional[float] = None
    pct_below_high: Optional[float] = None
    pct_above_low: Optional[float] = None
    reason: str = ''
    flags: list = field(default_factory=list)
    size_info: Optional[dict] = None


def score_ticker(
    df: pd.DataFrame,
    ticker: str,
    config: dict,
    earnings_date: Optional[date] = None,
    earnings_unknown: bool = False,
    as_of: Optional[date] = None,
) -> SignalResult:
    """
    Score a single ticker's OHLCV DataFrame against the Templar Code.

    Parameters
    ----------
    df              : OHLCV DataFrame, most-recent bar last
    ticker          : display name
    config          : full config dict (reads thresholds)
    earnings_date   : next earnings date from adapter (None = not fetched / unknown)
    earnings_unknown: True when the adapter couldn't return a date (different from None=none upcoming)
    as_of           : date to treat as "today" — default date.today(), overrideable in tests
    """
    if as_of is None:
        as_of = date.today()

    dc = donchian_channels(df)
    atr_series = compute_atr(df)
    trend = trend_state(df)

    thresholds = config.get('thresholds', {})
    min_avg_volume = thresholds.get('min_avg_volume', 1_000_000)
    extended_mult = thresholds.get('extended_atr_mult', 1.0)
    earnings_window = thresholds.get('earnings_window_days', 10)

    last = df.iloc[-1]
    close = float(last['close'])

    upper_20_raw = dc['upper_20'].iloc[-1]
    lower_20_raw = dc['lower_20'].iloc[-1]
    upper_55_raw = dc['upper_55'].iloc[-1]
    lower_55_raw = dc['lower_55'].iloc[-1]
    trail_high_10_raw = dc['trail_high_10'].iloc[-1]
    trail_low_10_raw = dc['trail_low_10'].iloc[-1]
    atr_raw = atr_series.iloc[-1]
    trend_val = str(trend.iloc[-1])

    # Insufficient data guard
    if any(np.isnan(float(v)) for v in [upper_20_raw, lower_20_raw, atr_raw]):
        return SignalResult(
            ticker=ticker, verdict=NO_SETUP,
            close=close,
            upper_20=float('nan'), lower_20=float('nan'),
            upper_55=float('nan'), lower_55=float('nan'),
            trail_high_10=float('nan'), trail_low_10=float('nan'),
            atr_20=float('nan'), trend=trend_val,
            reason='insufficient data for indicators',
        )

    upper_20 = float(upper_20_raw)
    lower_20 = float(lower_20_raw)
    upper_55 = float(upper_55_raw) if not np.isnan(float(upper_55_raw)) else float('nan')
    lower_55 = float(lower_55_raw) if not np.isnan(float(lower_55_raw)) else float('nan')
    trail_high_10 = float(trail_high_10_raw) if not np.isnan(float(trail_high_10_raw)) else float('nan')
    trail_low_10 = float(trail_low_10_raw) if not np.isnan(float(trail_low_10_raw)) else float('nan')
    atr_20 = float(atr_raw)

    avg_volume = float(df['volume'].tail(20).mean())

    # Proximity metrics (negative = already past the level)
    pct_below_high = (upper_20 - close) / upper_20 * 100 if upper_20 else None
    pct_above_low = (close - lower_20) / lower_20 * 100 if lower_20 else None

    flags: list[str] = []

    if avg_volume < min_avg_volume:
        flags.append(f'LOW_LIQUIDITY: avg 20-day vol {avg_volume:,.0f} < {min_avg_volume:,} threshold')

    flags.append('VERIFY: Check for news-driven distortion before acting.')

    def _earnings_flags(verdict: str) -> None:
        if verdict == NO_SETUP:
            return
        if earnings_unknown:
            flags.append('EARNINGS DATE UNKNOWN — verify manually before acting')
            return
        if earnings_date is not None:
            bd = pd.bdate_range(as_of, earnings_date)
            days_to = max(0, len(bd) - (1 if len(bd) > 0 and bd[-1].date() == earnings_date else 0))
            if days_to <= earnings_window:
                flags.append(
                    f'NO HOLD THROUGH EARNINGS: {earnings_date} is ~{days_to} trading day(s) away (Code rule)'
                )

    if trend_val == 'uptrend' and close > upper_20:
        entry_ref = upper_20
        stop_ref = entry_ref - 2 * atr_20
        trail_ref = trail_low_10

        if (close - upper_20) > extended_mult * atr_20:
            flags.append(f'EXTENDED: price is >{extended_mult} ATR past breakout level — chasing risk')

        _earnings_flags(LONG)

        return SignalResult(
            ticker=ticker, verdict=LONG,
            close=close,
            upper_20=upper_20, lower_20=lower_20,
            upper_55=upper_55, lower_55=lower_55,
            trail_high_10=trail_high_10, trail_low_10=trail_low_10,
            atr_20=atr_20, trend=trend_val,
            entry_ref=entry_ref, stop_ref=stop_ref, trail_ref=trail_ref,
            pct_below_high=pct_below_high,
            reason='close > upper_20 AND uptrend',
            flags=flags,
        )

    elif trend_val == 'downtrend' and close < lower_20:
        entry_ref = lower_20
        stop_ref = entry_ref + 2 * atr_20
        trail_ref = trail_high_10

        if (lower_20 - close) > extended_mult * atr_20:
            flags.append(f'EXTENDED: price is >{extended_mult} ATR past breakdown level — chasing risk')

        _earnings_flags(SHORT)

        return SignalResult(
            ticker=ticker, verdict=SHORT,
            close=close,
            upper_20=upper_20, lower_20=lower_20,
            upper_55=upper_55, lower_55=lower_55,
            trail_high_10=trail_high_10, trail_low_10=trail_low_10,
            atr_20=atr_20, trend=trend_val,
            entry_ref=entry_ref, stop_ref=stop_ref, trail_ref=trail_ref,
            pct_above_low=pct_above_low,
            reason='close < lower_20 AND downtrend',
            flags=flags,
        )

    else:
        parts = []
        if close <= upper_20 and upper_20:
            pct = (upper_20 - close) / upper_20 * 100
            parts.append(f'{pct:.1f}% below 20-day high ({upper_20:.2f})')
        elif close > upper_20 and trend_val != 'uptrend':
            parts.append(f'breakout up but trend={trend_val} (Vision veto)')

        if close >= lower_20 and lower_20:
            pct = (close - lower_20) / lower_20 * 100
            parts.append(f'{pct:.1f}% above 20-day low ({lower_20:.2f})')
        elif close < lower_20 and trend_val != 'downtrend':
            parts.append(f'breakdown but trend={trend_val} (Vision veto)')

        parts.append(f'trend={trend_val}')

        return SignalResult(
            ticker=ticker, verdict=NO_SETUP,
            close=close,
            upper_20=upper_20, lower_20=lower_20,
            upper_55=upper_55, lower_55=lower_55,
            trail_high_10=trail_high_10, trail_low_10=trail_low_10,
            atr_20=atr_20, trend=trend_val,
            pct_below_high=pct_below_high, pct_above_low=pct_above_low,
            reason='; '.join(parts),
            flags=[],
        )
