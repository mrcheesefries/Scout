"""
yfinance DataSource implementation.

This is the default source in v1. Swap for alpha_vantage.py etc. by changing
config.yaml — the rest of the codebase never imports yfinance directly.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from data.adapter import DataSource, DataSourceError

STALE_DAYS = 5   # Flag if latest bar is this many calendar days old
MIN_BARS = 60    # Minimum we'll accept (55-day channel needs ≥56 prior bars)


def check_staleness(ticker: str, df: pd.DataFrame, stale_days: int = STALE_DAYS) -> None:
    """
    Raise DataSourceError if the most-recent bar's date is older than stale_days.
    Extracted as a standalone function so tests can call it without mocking yfinance.
    """
    latest = df.index[-1]
    if hasattr(latest, 'date'):
        latest = latest.date()
    today = date.today()
    days_old = (today - latest).days
    if days_old > stale_days:
        raise DataSourceError(
            f'{ticker}: stale data — latest bar is {latest} ({days_old} calendar days ago, '
            f'max allowed {stale_days})'
        )


class YFinanceSource(DataSource):
    def get_ohlcv(self, ticker: str, bars: int = 120) -> pd.DataFrame:
        """
        Download OHLCV via yfinance.
        Raises DataSourceError if download fails, returns empty data, or is stale.
        """
        try:
            # Request extra history to ensure we have `bars` trading days after dropna
            raw = yf.download(
                ticker,
                period=f'{bars * 3}d',
                progress=False,
                auto_adjust=True,
                multi_level_column=False,
            )
        except Exception as exc:
            raise DataSourceError(f'{ticker}: yfinance download failed — {exc}') from exc

        if raw is None or raw.empty:
            raise DataSourceError(f'{ticker}: yfinance returned empty data')

        # Normalize column names to lowercase
        raw = raw.copy()
        raw.columns = [c.lower() for c in raw.columns]
        needed = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in needed if c not in raw.columns]
        if missing:
            raise DataSourceError(f'{ticker}: missing columns {missing} in yfinance response')

        df = raw[needed].dropna(how='all').tail(bars)

        if len(df) < MIN_BARS:
            raise DataSourceError(
                f'{ticker}: only {len(df)} bars returned after cleaning, '
                f'need at least {MIN_BARS}'
            )

        # Ensure index is plain date (not Timestamp) for consistency
        df.index = pd.to_datetime(df.index).normalize().date

        check_staleness(ticker, df)

        return df

    def get_earnings_date(self, ticker: str) -> Optional[date]:
        """
        Return next earnings date from yfinance, or None if unavailable.
        Does not raise — caller treats None as unknown.
        """
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is None or (hasattr(cal, 'empty') and cal.empty):
                return None
            # calendar is a dict in newer yfinance versions
            if isinstance(cal, dict):
                ed = cal.get('Earnings Date')
                if ed is None:
                    return None
                if not hasattr(ed, '__iter__') or isinstance(ed, str):
                    ed = [ed]
                today = date.today()
                future = [
                    pd.Timestamp(d).date() for d in ed
                    if pd.Timestamp(d).date() >= today
                ]
                return min(future) if future else None
            # Older yfinance: DataFrame with index
            if hasattr(cal, 'loc') and 'Earnings Date' in cal.index:
                ed = cal.loc['Earnings Date']
                if not hasattr(ed, '__iter__') or isinstance(ed, str):
                    ed = [ed]
                today = date.today()
                future = [
                    pd.Timestamp(d).date() for d in ed
                    if pd.Timestamp(d).date() >= today
                ]
                return min(future) if future else None
            return None
        except Exception:
            return None
