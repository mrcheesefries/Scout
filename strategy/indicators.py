"""
Pure indicator math — data in, numbers out, zero I/O.

THE CRITICAL RULE (§2.1): Donchian channels exclude the current bar.
Use .shift(1) before .rolling() so bar N uses bars N-period..N-1 only.
Without this, every bar is trivially its own 20-day high.
"""
import numpy as np
import pandas as pd


def donchian_channels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Donchian channels with lookahead-safe lookback.
    All levels use .shift(1) so current bar is excluded from its own level.

    Returns DataFrame with columns:
      upper_20, lower_20, upper_55, lower_55, trail_high_10, trail_low_10
    """
    h = df['high'].shift(1)
    lo = df['low'].shift(1)

    result = pd.DataFrame(index=df.index)
    result['upper_20'] = h.rolling(20).max()
    result['lower_20'] = lo.rolling(20).min()
    result['upper_55'] = h.rolling(55).max()
    result['lower_55'] = lo.rolling(55).min()
    result['trail_high_10'] = h.rolling(10).max()
    result['trail_low_10'] = lo.rolling(10).min()
    return result


def atr(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Wilder's Average True Range.

    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    Seed: SMA of first `period` valid TRs.
    Subsequent: ATR_i = (ATR_{i-1} * (period-1) + TR_i) / period
    """
    prev_close = df['close'].shift(1)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - prev_close).abs(),
        (df['low'] - prev_close).abs(),
    ], axis=1).max(axis=1)

    tr_arr = tr.values.astype(float)
    atr_arr = np.full(len(tr_arr), np.nan)

    valid_mask = ~np.isnan(tr_arr)
    if not valid_mask.any():
        return pd.Series(atr_arr, index=df.index)

    first_idx = int(np.argmax(valid_mask))

    if first_idx + period > len(tr_arr):
        return pd.Series(atr_arr, index=df.index)

    seed_end = first_idx + period
    atr_arr[seed_end - 1] = float(np.mean(tr_arr[first_idx:seed_end]))

    for i in range(seed_end, len(tr_arr)):
        if not np.isnan(tr_arr[i]):
            atr_arr[i] = (atr_arr[i - 1] * (period - 1) + tr_arr[i]) / period
        else:
            atr_arr[i] = atr_arr[i - 1]

    return pd.Series(atr_arr, index=df.index)


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(period).mean()


def trend_state(df: pd.DataFrame) -> pd.Series:
    """
    Returns a Series of 'uptrend', 'downtrend', or 'no_trend' per bar.

    Uptrend:   close > SMA_50  AND  SMA_50 > SMA_200
    Downtrend: close < SMA_50  AND  SMA_50 < SMA_200
    Otherwise: no_trend
    """
    close = df['close']
    sma50 = sma(close, 50)
    sma200 = sma(close, 200)

    result = pd.Series('no_trend', index=df.index, dtype=object)
    result[(close > sma50) & (sma50 > sma200)] = 'uptrend'
    result[(close < sma50) & (sma50 < sma200)] = 'downtrend'
    return result
