"""
Scout orchestrator — single daily run.

Load config → fetch OHLCV → score signals → write results.json + index.html
→ append history log.

The Scout reads. The Scout never executes.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from data.adapter import DataSourceError
from data.yfinance_source import YFinanceSource
from report.builder import build_results
from report.dashboard import render_dashboard
from strategy.signals import score_ticker
from strategy.sizing import position_size

CONFIG_PATH = Path('config.yaml')
OUTPUT_DIR = Path('output')
HISTORY_DIR = Path('history')


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def flatten_watchlist(watchlist: dict) -> list[tuple[str, str]]:
    """Return [(ticker, sector), ...] from the nested watchlist dict."""
    tickers = []
    for sector, names in watchlist.items():
        for name in (names or []):
            tickers.append((str(name), sector))
    return tickers


def run() -> dict:
    config = load_config()

    # Account value: env var overrides committed config (which should be null)
    account_value = 0.0
    env_val = os.environ.get('ACCOUNT_VALUE')
    if env_val:
        try:
            account_value = float(env_val)
        except ValueError:
            print(f'WARNING: ACCOUNT_VALUE env var "{env_val}" is not a valid number, ignoring')
    elif config.get('account_value'):
        account_value = float(config['account_value'])

    source = YFinanceSource()
    tickers = flatten_watchlist(config.get('watchlist', {}))

    results: list[dict] = []
    data_errors: list[dict] = []

    earnings_window = config.get('thresholds', {}).get('earnings_window_days', 10)

    for ticker, sector in tickers:
        print(f'  Scanning {ticker}...', end='', flush=True)
        try:
            df = source.get_ohlcv(ticker, bars=120)

            # Best-effort earnings date (failure → flag as unknown)
            earnings_date = None
            earnings_unknown = False
            try:
                earnings_date = source.get_earnings_date(ticker)
            except Exception:
                earnings_unknown = True

            signal = score_ticker(
                df, ticker, config,
                earnings_date=earnings_date,
                earnings_unknown=earnings_unknown,
            )

            results.append({'sector': sector, 'signal': signal})
            print(f' {signal.verdict}')

        except DataSourceError as exc:
            print(f' DATA ERROR')
            data_errors.append({'ticker': ticker, 'error': str(exc)})
        except Exception as exc:
            print(f' ERROR: {exc}')
            data_errors.append({'ticker': ticker, 'error': f'Unexpected error: {exc}'})

    run_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    output = build_results(results, data_errors, run_ts, account_value, config)

    OUTPUT_DIR.mkdir(exist_ok=True)
    results_path = OUTPUT_DIR / 'results.json'
    results_path.write_text(json.dumps(output, indent=2, default=str))

    html = render_dashboard(output)
    (OUTPUT_DIR / 'index.html').write_text(html)

    HISTORY_DIR.mkdir(exist_ok=True)
    log_entry = {
        'run_timestamp': run_ts,
        'setups': len(output.get('setups', [])),
        'errors': len(data_errors),
        'tickers_scanned': len(results),
    }
    with open(HISTORY_DIR / 'log.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    return output


def main() -> None:
    print('Scout starting...')
    output = run()

    setups = output.get('setups', [])
    errors = output.get('data_errors', [])

    print(f'\n{"=" * 50}')
    if errors:
        print(f'DATA ERRORS ({len(errors)}):')
        for e in errors:
            print(f'  DATA ERROR: {e["ticker"]} — {e["error"]}')

    if setups:
        print(f'\nSETUPS FOUND ({len(setups)}):')
        for s in setups:
            print(f'  {s["ticker"]}: {s["verdict"]} — entry ref {s.get("entry_ref")}, stop ref {s.get("stop_ref")}')
    else:
        print('\nNO SETUP — stand down.')

    print(f'\nOutput: {OUTPUT_DIR / "index.html"}')
    print('The Scout has spoken. It never executes.')


if __name__ == '__main__':
    main()
