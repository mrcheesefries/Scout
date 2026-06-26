"""
Abstract DataSource interface.

Every data provider implements this. The strategy and report modules
import only this interface — never yfinance or any concrete source.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataSourceError(Exception):
    """
    Raised when a fetch fails, returns empty data, or returns stale data.
    Must never be swallowed silently — surfaces as DATA ERROR in the report.
    """


class DataSource(ABC):
    @abstractmethod
    def get_ohlcv(self, ticker: str, bars: int = 120) -> pd.DataFrame:
        """
        Return OHLCV DataFrame: index=date, columns=[open, high, low, close, volume].
        Most-recent bar is last. Raises DataSourceError on any failure.
        NEVER returns empty or partial data silently.
        """

    @abstractmethod
    def get_earnings_date(self, ticker: str) -> date | None:
        """
        Return the next earnings date, or None if unknown / none upcoming.
        Should not raise — return None on failure and let the caller flag it.
        """
