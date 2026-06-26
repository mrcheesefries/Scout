# The Scout

> Edge scanner for The Templar Order. Read-only. Scans a watchlist daily, scores each name against the Code, recommends setups or declares "no setup." Outputs an HTML dashboard viewable on mobile via GitHub Pages.

## The One Rule Above All

**The Scout NEVER places, modifies, or routes an order.** There is no exchange write access, no API keys with trade permissions, no order code path anywhere in this codebase. It reads market data, computes signals, writes a report. That is the entire job.

Suggest, never execute. This is an architectural wall, not a config flag.

---

## What It Does (one daily run)

1. Loads your watchlist from `config.yaml`
2. Pulls daily OHLCV history for each ticker (≥ 60 bars via yfinance)
3. Computes the Templar signal stack: Donchian channels, ATR, SMA trend filter
4. Scores each name: **LONG setup / SHORT setup / NO SETUP**, with honesty flags
5. Writes `output/results.json` (data) and `output/index.html` (dashboard)
6. GitHub Pages serves the dashboard — open on your phone for a daily glance

---

## The Strategy Logic

**Donchian channel (the Sword):**
- `upper_20` = highest HIGH over the **prior** 20 bars (excluding the current bar — critical anti-lookahead rule)
- LONG setup: `close > upper_20` AND trend is uptrend

**Trend proxy (the Vision — v1 daily only):**
- Uptrend: `close > SMA_50 > SMA_200`
- Downtrend: `close < SMA_50 < SMA_200`
- Otherwise: NO TREND → no trade

**Position sizing (informational, never executed):**
- 1% risk: `shares = floor((account_value × 0.01) / (2 × ATR))`
- Shown on setup cards so you can place manually on Revolut

---

## Configure the Watchlist

Edit `config.yaml`:

```yaml
watchlist:
  semis:    [NVDA, AMD, AVGO, MU]
  etfs:     [SPY, QQQ]
  crypto:   [BTC-USD, ETH-USD]

thresholds:
  min_avg_volume: 1000000      # flag thin names
  extended_atr_mult: 1.0       # flag "chasing" entries
  earnings_window_days: 10     # flag names with earnings < 10 days out
```

Use any ticker supported by yfinance (equities, ETFs, crypto like `BTC-USD`).

---

## Account Value (Sizing Estimates)

**Do NOT hardcode your account value in `config.yaml`** — the repo is public.

Set it as a GitHub Secret:
1. Go to **Settings → Secrets and variables → Actions**
2. Add secret: `ACCOUNT_VALUE` = your portfolio value (e.g. `33800`)
3. The CI workflow injects it as an env var at run time

Sizing estimates will show `0 shares` until the secret is configured. All signal logic works normally regardless.

---

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: set account value for sizing estimates
export ACCOUNT_VALUE=10000

# Run the scanner
python main.py

# Open the dashboard
open output/index.html
```

---

## Run Tests

```bash
pip install pytest
pytest
```

All 8 acceptance tests from the spec must pass. The most important is `test_no_lookahead_donchian_20` — if that fails, the entire scanner is lying.

---

## How the Daily Cron Works

GitHub Actions runs on schedule `0 2 * * 2-6` (02:00 UTC Tuesday–Saturday):
- This covers Monday–Friday US sessions (US close = 16:00 ET = ~21:00 UTC; we run 5h after)
- The +1 UTC-day offset is intentional: a post-close run lands on the next calendar day

**On each run:**
1. Scanner runs, writes `output/results.json` + `output/index.html`
2. Results committed to the repo
3. GitHub Pages deploys from `output/`

**If the run fails:** nothing is committed. The last-good dashboard stays up with its (now visibly stale) timestamp. The stale warning is shown prominently.

**Manual run:** go to Actions tab → "Scout Daily Run" → "Run workflow".

---

## Dashboard Features

- **Run timestamp + data date** shown prominently — stale runs are flagged visibly
- **VERDICT banner** — big and clear
- **Setup cards** — entry ref, stop ref, trail ref, 1% size estimate, honesty flags
- **Watchlist proximity table** — every name sorted by distance to breakout
- **Data health section** — any failed fetches listed explicitly
- **Footer** — "Scout suggests. It never executes."

---

## Architecture

```
strategy/   ← pure functions (data in, numbers out — no I/O, fully testable)
  indicators.py   ← Donchian, ATR, SMA/trend
  signals.py      ← scoring: LONG / SHORT / NO SETUP
  sizing.py       ← 1% position calc (informational)

data/       ← network boundary
  adapter.py          ← abstract DataSource interface
  yfinance_source.py  ← default implementation

report/     ← output generation
  builder.py      ← results.json structure
  dashboard.py    ← index.html renderer

tests/      ← acceptance tests (§7 — all mandatory)
output/     ← generated files (committed by CI)
history/    ← log.jsonl — one line per run
```

---

*The Scout suggests. It never executes. Process over outcome. Patience. Position. Process.*
