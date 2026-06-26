"""
Build the results.json structure from raw scan output.

Pure transformation — no I/O. Deterministic: same inputs → same output.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from strategy.signals import SignalResult, LONG, SHORT
from strategy.sizing import position_size


def _safe_float(v) -> Any:
    """Convert NaN/inf to None for JSON safety."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _signal_to_dict(signal: SignalResult, sector: str, account_value: float) -> dict:
    size = None
    if signal.verdict in (LONG, SHORT) and account_value and account_value > 0:
        size = position_size(account_value, signal.entry_ref, signal.stop_ref)

    return {
        'ticker': signal.ticker,
        'sector': sector,
        'verdict': signal.verdict,
        'close': _safe_float(signal.close),
        'upper_20': _safe_float(signal.upper_20),
        'lower_20': _safe_float(signal.lower_20),
        'upper_55': _safe_float(signal.upper_55),
        'lower_55': _safe_float(signal.lower_55),
        'trail_high_10': _safe_float(signal.trail_high_10),
        'trail_low_10': _safe_float(signal.trail_low_10),
        'atr_20': _safe_float(signal.atr_20),
        'trend': signal.trend,
        'entry_ref': _safe_float(signal.entry_ref),
        'stop_ref': _safe_float(signal.stop_ref),
        'trail_ref': _safe_float(signal.trail_ref),
        'pct_below_high': _safe_float(signal.pct_below_high),
        'pct_above_low': _safe_float(signal.pct_above_low),
        'reason': signal.reason,
        'flags': list(signal.flags),
        'size': size,
    }


def _market_state(watchlist_dicts: list[dict]) -> str:
    """Derive market state from SPY's trend if SPY is in the watchlist."""
    for row in watchlist_dicts:
        if row['ticker'] in ('SPY', 'QQQ'):
            trend = row.get('trend', '')
            if trend == 'uptrend':
                return 'RISK-ON'
            if trend == 'downtrend':
                return 'RISK-OFF'
            return 'MIXED'
    return 'UNKNOWN'


def build_results(
    results: list[dict],
    data_errors: list[dict],
    run_timestamp: str,
    account_value: float,
    config: dict,
) -> dict:
    """
    Build the canonical results dict (serialised to results.json).

    Parameters
    ----------
    results       : list of {'sector': str, 'signal': SignalResult}
    data_errors   : list of {'ticker': str, 'error': str}
    run_timestamp : ISO date string of this run
    account_value : portfolio value used for sizing (0 = not set)
    config        : full config dict (unused here but available for future use)
    """
    rows = [
        _signal_to_dict(item['signal'], item['sector'], account_value)
        for item in results
    ]

    setups = [r for r in rows if r['verdict'] in (LONG, SHORT)]

    # Sort watchlist by proximity to breakout:
    # pct_below_high negative = already broke out (sorts first),
    # large positive = far from breakout (sorts last)
    def _sort_key(r):
        pct = r.get('pct_below_high')
        return pct if pct is not None else 9999.0

    watchlist = sorted(rows, key=_sort_key)

    market_state = _market_state(rows)

    return {
        'run_timestamp': run_timestamp,
        'scan_date': date.today().isoformat(),
        'market_state': market_state,
        'setup_count': len(setups),
        'setups': setups,
        'watchlist': watchlist,
        'data_errors': data_errors,
        'account_value_estimate': account_value if account_value and account_value > 0 else None,
    }
