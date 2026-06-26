"""
Position sizing — informational only.

The Scout NEVER places orders. This computes what a 1% risk-per-trade
position *would* look like so the report is actionable when you place
it manually on Revolut.
"""
import math


def position_size(account_value: float, entry_ref: float, stop_ref: float) -> dict:
    """
    1% risk sizing.

    risk_per_share = |entry_ref - stop_ref|   (= 2 * ATR for Templar setups)
    shares         = floor((account_value * 0.01) / risk_per_share)
    notional       = shares * entry_ref

    Returns dict with shares, notional, risk_per_share.
    Returns zeros if any input is invalid.
    """
    if account_value <= 0 or entry_ref <= 0:
        return {'shares': 0, 'notional': 0.0, 'risk_per_share': 0.0}

    risk_per_share = abs(entry_ref - stop_ref)
    if risk_per_share <= 0:
        return {'shares': 0, 'notional': 0.0, 'risk_per_share': 0.0}

    shares = math.floor((account_value * 0.01) / risk_per_share)
    notional = shares * entry_ref

    return {
        'shares': shares,
        'notional': round(notional, 2),
        'risk_per_share': round(risk_per_share, 4),
    }
