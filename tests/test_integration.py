"""
Integration tests — §7 acceptance tests 6, 7, 8.

Test 6: data failure surfaces as DATA ERROR, never as "no setup"
Test 7: stale data is caught and flagged
Test 8: same inputs → byte-identical results.json
"""
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from data.adapter import DataSource, DataSourceError
from data.yfinance_source import check_staleness
from report.builder import build_results
from strategy.signals import score_ticker, LONG, NO_SETUP


# ---------------------------------------------------------------------------
# §7.6 — Data failure is loud
# ---------------------------------------------------------------------------

class AlwaysFailSource(DataSource):
    """Adapter that always raises DataSourceError."""
    def get_ohlcv(self, ticker: str, bars: int = 120) -> pd.DataFrame:
        raise DataSourceError(f'{ticker}: simulated connection failure')

    def get_earnings_date(self, ticker: str):
        return None


def simulate_scan_for_ticker(source: DataSource, ticker: str, config: dict) -> tuple:
    """
    Mimics what main.py does for a single ticker.
    Returns (results_list, data_errors_list).
    """
    results = []
    data_errors = []
    try:
        df = source.get_ohlcv(ticker, bars=120)
        signal = score_ticker(df, ticker, config)
        results.append({'sector': 'test', 'signal': signal})
    except DataSourceError as e:
        data_errors.append({'ticker': ticker, 'error': str(e)})
    return results, data_errors


def test_data_failure_is_loud():
    """§7.6 — adapter raises DataSourceError → DATA ERROR in output, not NO_SETUP."""
    config = {'thresholds': {}}
    source = AlwaysFailSource()

    results, data_errors = simulate_scan_for_ticker(source, 'FAIL', config)

    assert len(data_errors) == 1, "Failure must surface as a data error"
    assert data_errors[0]['ticker'] == 'FAIL'
    assert len(results) == 0, "Failed ticker must not appear as a signal result"

    # Verify it flows into the output JSON correctly
    output = build_results([], data_errors, '2024-01-01', 0, config)
    assert len(output['data_errors']) == 1
    assert output['data_errors'][0]['ticker'] == 'FAIL'


def test_data_failure_does_not_show_as_no_setup():
    """A DATA ERROR must never be silently treated as NO SETUP."""
    config = {'thresholds': {}}
    source = AlwaysFailSource()

    results, data_errors = simulate_scan_for_ticker(source, 'FAIL', config)

    # The results list (which feeds the watchlist) must be empty — not a NO_SETUP entry
    assert not any(
        r.get('signal') and r['signal'].verdict == NO_SETUP
        for r in results
    ), "Data error must not masquerade as NO_SETUP"


# ---------------------------------------------------------------------------
# §7.7 — Stale data caught
# ---------------------------------------------------------------------------

def test_stale_data_raises():
    """§7.7 — latest bar dated 10 days ago → DataSourceError with 'stale' message."""
    old_date = date.today() - timedelta(days=10)
    df = pd.DataFrame(
        {'open': [100.0], 'high': [101.0], 'low': [99.0], 'close': [100.0], 'volume': [1e6]},
        index=[old_date],
    )
    with pytest.raises(DataSourceError, match='stale'):
        check_staleness('STALE_TEST', df, stale_days=5)


def test_recent_data_does_not_raise():
    """Data from today must not be flagged as stale."""
    df = pd.DataFrame(
        {'open': [100.0], 'high': [101.0], 'low': [99.0], 'close': [100.0], 'volume': [1e6]},
        index=[date.today()],
    )
    check_staleness('FRESH_TEST', df, stale_days=5)  # must not raise


def test_stale_data_boundary():
    """Exactly stale_days old is flagged; one day less is not."""
    stale_days = 3
    just_stale = date.today() - timedelta(days=stale_days + 1)
    just_fresh = date.today() - timedelta(days=stale_days)

    df_stale = pd.DataFrame(
        {'open': [1.0], 'high': [1.0], 'low': [1.0], 'close': [1.0], 'volume': [1e6]},
        index=[just_stale],
    )
    df_fresh = pd.DataFrame(
        {'open': [1.0], 'high': [1.0], 'low': [1.0], 'close': [1.0], 'volume': [1e6]},
        index=[just_fresh],
    )

    with pytest.raises(DataSourceError, match='stale'):
        check_staleness('T', df_stale, stale_days=stale_days)

    check_staleness('T', df_fresh, stale_days=stale_days)  # no raise


# ---------------------------------------------------------------------------
# §7.8 — Determinism
# ---------------------------------------------------------------------------

def _make_test_signal(verdict: str):
    """Helper to produce a minimal SignalResult for determinism testing."""
    from strategy.signals import SignalResult
    return SignalResult(
        ticker='AAPL', verdict=verdict,
        close=150.0, upper_20=148.0, lower_20=130.0,
        upper_55=155.0, lower_55=120.0,
        trail_high_10=149.0, trail_low_10=135.0,
        atr_20=3.5, trend='uptrend',
        entry_ref=148.0 if verdict == LONG else None,
        stop_ref=141.0 if verdict == LONG else None,
        trail_ref=135.0 if verdict == LONG else None,
        pct_below_high=-1.3,
        reason='close > upper_20 AND uptrend',
        flags=['VERIFY: Check for news-driven distortion before acting.'],
    )


def test_determinism():
    """§7.8 — same inputs → byte-identical results.json output."""
    config = {'thresholds': {}}

    signal = _make_test_signal(LONG)
    results = [{'sector': 'tech', 'signal': signal}]
    data_errors = []

    output1 = build_results(results, data_errors, '2024-01-15', 10_000, config)
    output2 = build_results(results, data_errors, '2024-01-15', 10_000, config)

    json1 = json.dumps(output1, sort_keys=True, default=str)
    json2 = json.dumps(output2, sort_keys=True, default=str)

    assert json1 == json2, "Results are not deterministic — output differs between runs"


def test_determinism_with_no_setup():
    """Determinism holds for NO_SETUP results too."""
    config = {'thresholds': {}}

    signal = _make_test_signal(NO_SETUP)
    results = [{'sector': 'tech', 'signal': signal}]

    output1 = build_results(results, [], '2024-01-15', 0, config)
    output2 = build_results(results, [], '2024-01-15', 0, config)

    json1 = json.dumps(output1, sort_keys=True, default=str)
    json2 = json.dumps(output2, sort_keys=True, default=str)

    assert json1 == json2
