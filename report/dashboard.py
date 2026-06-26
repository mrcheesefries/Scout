"""
Render the self-contained index.html dashboard from a results dict.

The JSON is inlined into the HTML so the file loads instantly on mobile
with no fetch/CORS issues on GitHub Pages.
"""
from __future__ import annotations

import json
from typing import Any


def render_dashboard(data: dict) -> str:
    """
    Render a single self-contained HTML file with results inlined as JSON.
    """
    json_str = json.dumps(data, indent=2, default=str)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Scout — Templar Edge Scanner</title>
<style>
:root {{
  --bg:     #0e1116;
  --card:   #161b22;
  --border: #30363d;
  --text:   #e6edf3;
  --muted:  #8b949e;
  --long:   #2ea043;
  --short:  #a371f7;
  --stop:   #f85149;
  --gold:   #c9a227;
  --warn:   #d29922;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', ui-monospace, monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 0 0 48px 0;
}}
a {{ color: var(--gold); }}

/* Header */
.header {{
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}}
.header-title {{
  font-size: 18px;
  font-weight: 700;
  color: var(--gold);
  letter-spacing: 0.05em;
  flex: 1 1 auto;
}}
.chip {{
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
  border: 1px solid var(--border);
  color: var(--muted);
  white-space: nowrap;
}}
.chip.risk-on  {{ border-color: var(--long);  color: var(--long);  }}
.chip.risk-off {{ border-color: var(--short); color: var(--short); }}
.chip.mixed    {{ border-color: var(--warn);  color: var(--warn);  }}
.chip.setups   {{ border-color: var(--gold);  color: var(--gold);  }}
.ts {{ font-size: 11px; color: var(--muted); }}
.stale-banner {{
  background: #3d2b00;
  border: 1px solid var(--warn);
  color: var(--warn);
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}}

/* Verdict banner */
.verdict-banner {{
  margin: 16px;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.05em;
  border: 2px solid;
}}
.verdict-banner.long  {{ background: #0d2318; border-color: var(--long);  color: var(--long);  }}
.verdict-banner.short {{ background: #1f1133; border-color: var(--short); color: var(--short); }}
.verdict-banner.none  {{ background: #1a1c22; border-color: var(--border); color: var(--muted); }}

/* Cards */
.section-title {{
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 20px 16px 8px;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin: 0 16px 12px;
  padding: 14px;
}}
.card.long-card  {{ border-left: 3px solid var(--long);  }}
.card.short-card {{ border-left: 3px solid var(--short); }}

.card-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}}
.ticker {{
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.03em;
}}
.verdict-tag {{
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}}
.verdict-tag.long  {{ background: var(--long);  color: #fff; }}
.verdict-tag.short {{ background: var(--short); color: #fff; }}
.sector-tag {{
  font-size: 11px;
  color: var(--muted);
  margin-left: auto;
}}

.levels {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin: 10px 0;
}}
.level-box {{
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
}}
.level-label {{
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.level-value {{
  font-size: 15px;
  font-weight: 700;
  margin-top: 2px;
}}
.level-value.entry {{ color: var(--text); }}
.level-value.stop  {{ color: var(--stop); }}
.level-value.trail {{ color: var(--warn); }}

.size-row {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin: 10px 0;
  font-size: 12px;
  color: var(--muted);
}}
.size-row span {{ font-weight: 600; color: var(--text); }}

.flags {{
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}}
.flag {{
  font-size: 12px;
  padding: 5px 9px;
  border-radius: 4px;
  background: #1f2229;
  border-left: 3px solid var(--warn);
  color: var(--warn);
  line-height: 1.4;
}}
.flag.earnings {{ border-color: var(--stop); color: var(--stop); }}
.flag.verify   {{ border-color: var(--border); color: var(--muted); }}
.flag.liquidity {{ border-color: var(--short); color: var(--short); }}
.flag.extended  {{ border-color: var(--warn); color: var(--warn); }}

/* Watchlist table */
.table-wrap {{ overflow-x: auto; margin: 0 16px; }}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
th {{
  text-align: left;
  padding: 7px 10px;
  color: var(--muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}}
td {{
  padding: 7px 10px;
  border-bottom: 1px solid #1e2430;
  white-space: nowrap;
}}
tr:hover td {{ background: #1a2030; }}
.td-long   {{ color: var(--long);  font-weight: 700; }}
.td-short  {{ color: var(--short); font-weight: 700; }}
.td-none   {{ color: var(--muted); }}
.bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
.prox-bar {{
  flex: 1;
  min-width: 40px;
  max-width: 80px;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}}
.prox-fill {{ height: 100%; border-radius: 2px; background: var(--gold); }}

/* Data health */
.error-list {{
  margin: 0 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.error-row {{
  background: #2d1113;
  border: 1px solid var(--stop);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--stop);
}}
.error-ticker {{ font-weight: 700; }}
.error-msg {{ color: #f07b78; margin-top: 2px; font-size: 11px; }}
.no-errors {{
  font-size: 12px;
  color: var(--muted);
  margin: 0 16px;
  padding: 8px 0;
}}

/* Footer */
footer {{
  margin: 32px 16px 0;
  padding: 16px 0 0;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  line-height: 1.7;
}}
</style>
</head>
<body>
<script>
const SCOUT_DATA = {json_str};

// ─── Utilities ───────────────────────────────────────────────────────────────

function fmt(v, decimals = 2) {{
  if (v == null || isNaN(v)) return '—';
  return Number(v).toFixed(decimals);
}}

function fmtPct(v) {{
  if (v == null || isNaN(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return sign + Number(v).toFixed(1) + '%';
}}

function fmtNum(v) {{
  if (v == null || isNaN(v)) return '—';
  return Number(v).toLocaleString();
}}

function el(tag, cls, inner) {{
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (inner != null) d.innerHTML = inner;
  return d;
}}

function isTodayUtc(dateStr) {{
  const today = new Date();
  const todayStr = today.getUTCFullYear() + '-' +
    String(today.getUTCMonth() + 1).padStart(2, '0') + '-' +
    String(today.getUTCDate()).padStart(2, '0');
  return dateStr === todayStr;
}}

function flagClass(f) {{
  f = f.toUpperCase();
  if (f.includes('EARNINGS') || f.includes('HOLD')) return 'earnings';
  if (f.includes('LIQUIDITY')) return 'liquidity';
  if (f.includes('EXTENDED')) return 'extended';
  if (f.includes('VERIFY') || f.includes('NEWS')) return 'verify';
  return '';
}}

// ─── Header ──────────────────────────────────────────────────────────────────

function renderHeader() {{
  const d = SCOUT_DATA;
  const isStale = !isTodayUtc(d.scan_date);

  if (isStale) {{
    const b = el('div', 'stale-banner',
      '⚠ STALE DATA — Last run: ' + d.run_timestamp + ' | Today is not ' + d.scan_date +
      ' — the scheduled run may have missed or be delayed.');
    document.body.prepend(b);
  }}

  const ms = d.market_state || 'UNKNOWN';
  const msClass = ms === 'RISK-ON' ? 'risk-on' : ms === 'RISK-OFF' ? 'risk-off' : 'mixed';

  const header = el('div', 'header');
  header.innerHTML = `
    <div class="header-title">⚔ THE SCOUT</div>
    <div class="chip ${{msClass}}">${{ms}}</div>
    ${{d.setup_count > 0 ? `<div class="chip setups">${{d.setup_count}} SETUP${{d.setup_count > 1 ? 'S' : ''}}</div>` : ''}}
    <div class="ts">Run: ${{d.run_timestamp}} UTC &nbsp;|&nbsp; Data: ${{d.scan_date}}</div>
  `;
  document.body.appendChild(header);
}}

// ─── Verdict Banner ───────────────────────────────────────────────────────────

function renderVerdict() {{
  const d = SCOUT_DATA;
  const setups = d.setups || [];
  const longs = setups.filter(s => s.verdict === 'LONG').length;
  const shorts = setups.filter(s => s.verdict === 'SHORT').length;

  let cls, text;
  if (longs > 0 && shorts > 0) {{
    cls = 'long';
    text = `⚔ ${{longs}} LONG SETUP${{longs > 1 ? 'S' : ''}} + ${{shorts}} SHORT SETUP${{shorts > 1 ? 'S' : ''}}`;
  }} else if (longs > 0) {{
    cls = 'long';
    text = `⚔ ${{longs}} LONG SETUP${{longs > 1 ? 'S' : ''}}`;
  }} else if (shorts > 0) {{
    cls = 'short';
    text = `⚔ ${{shorts}} SHORT SETUP${{shorts > 1 ? 'S' : ''}}`;
  }} else {{
    cls = 'none';
    text = 'NO SETUP — STAND DOWN';
  }}

  document.body.appendChild(el('div', `verdict-banner ${{cls}}`, text));
}}

// ─── Setup Cards ─────────────────────────────────────────────────────────────

function renderSetups() {{
  const setups = SCOUT_DATA.setups || [];
  if (setups.length === 0) return;

  document.body.appendChild(el('div', 'section-title', 'SETUPS'));

  setups.forEach(s => {{
    const cardCls = s.verdict === 'LONG' ? 'card long-card' : 'card short-card';
    const card = el('div', cardCls);

    // Header row
    const hdr = el('div', 'card-header');
    hdr.innerHTML = `
      <div class="ticker">${{s.ticker}}</div>
      <div class="verdict-tag ${{s.verdict.toLowerCase()}}">${{s.verdict}}</div>
      <div class="sector-tag">${{s.sector || ''}}</div>
    `;
    card.appendChild(hdr);

    // Level boxes
    const levels = el('div', 'levels');
    levels.innerHTML = `
      <div class="level-box">
        <div class="level-label">Close</div>
        <div class="level-value entry">${{fmt(s.close)}}</div>
      </div>
      <div class="level-box">
        <div class="level-label">Entry Ref</div>
        <div class="level-value entry">${{fmt(s.entry_ref)}}</div>
      </div>
      <div class="level-box">
        <div class="level-label">Stop Ref</div>
        <div class="level-value stop">${{fmt(s.stop_ref)}}</div>
      </div>
      <div class="level-box">
        <div class="level-label">Trail Ref</div>
        <div class="level-value trail">${{fmt(s.trail_ref)}}</div>
      </div>
      <div class="level-box">
        <div class="level-label">ATR(20)</div>
        <div class="level-value entry">${{fmt(s.atr_20)}}</div>
      </div>
    `;
    card.appendChild(levels);

    // Size info
    if (s.size && s.size.shares > 0) {{
      const sz = el('div', 'size-row');
      sz.innerHTML = `
        Est. 1% size (account ~${{fmtNum(SCOUT_DATA.account_value_estimate)}}):
        &nbsp;<span>${{s.size.shares}} shares</span>
        &nbsp;· notional <span>$${{fmtNum(Math.round(s.size.notional))}}</span>
        &nbsp;· risk/share <span>${{fmt(s.size.risk_per_share)}}</span>
      `;
      card.appendChild(sz);
    }}

    // Flags
    const flags = s.flags || [];
    if (flags.length > 0) {{
      const flagsDiv = el('div', 'flags');
      flags.forEach(f => {{
        flagsDiv.appendChild(el('div', `flag ${{flagClass(f)}}`, f));
      }});
      card.appendChild(flagsDiv);
    }}

    document.body.appendChild(card);
  }});
}}

// ─── Watchlist Table ─────────────────────────────────────────────────────────

function renderWatchlist() {{
  const rows = SCOUT_DATA.watchlist || [];
  document.body.appendChild(el('div', 'section-title', 'WATCHLIST — proximity to breakout'));

  const wrap = el('div', 'table-wrap');
  const t = el('table');
  t.innerHTML = `
    <thead><tr>
      <th>Ticker</th>
      <th>Sector</th>
      <th>Close</th>
      <th>20d High</th>
      <th>% Below</th>
      <th>Proximity</th>
      <th>Trend</th>
      <th>Verdict</th>
    </tr></thead>
  `;
  const tbody = el('tbody');

  rows.forEach(r => {{
    const tr = document.createElement('tr');
    const pct = r.pct_below_high;
    const fillPct = pct == null ? 0 : Math.max(0, Math.min(100, 100 - pct));

    const verdictCls = r.verdict === 'LONG' ? 'td-long' :
                       r.verdict === 'SHORT' ? 'td-short' : 'td-none';

    tr.innerHTML = `
      <td><b>${{r.ticker}}</b></td>
      <td class="td-none">${{r.sector || ''}}</td>
      <td>${{fmt(r.close)}}</td>
      <td>${{fmt(r.upper_20)}}</td>
      <td>${{fmtPct(pct)}}</td>
      <td>
        <div class="bar-wrap">
          <div class="prox-bar">
            <div class="prox-fill" style="width: ${{fillPct}}%"></div>
          </div>
        </div>
      </td>
      <td class="td-none">${{r.trend || '—'}}</td>
      <td class="${{verdictCls}}">${{r.verdict}}</td>
    `;
    tbody.appendChild(tr);
  }});

  t.appendChild(tbody);
  wrap.appendChild(t);
  document.body.appendChild(wrap);
}}

// ─── Data Health ─────────────────────────────────────────────────────────────

function renderDataHealth() {{
  const errors = SCOUT_DATA.data_errors || [];
  document.body.appendChild(el('div', 'section-title', 'DATA HEALTH'));

  if (errors.length === 0) {{
    document.body.appendChild(el('div', 'no-errors', '✓ All tickers fetched successfully.'));
    return;
  }}

  const list = el('div', 'error-list');
  errors.forEach(e => {{
    const row = el('div', 'error-row');
    row.innerHTML = `
      <div class="error-ticker">DATA ERROR: ${{e.ticker}}</div>
      <div class="error-msg">${{e.error}}</div>
    `;
    list.appendChild(row);
  }});

  // Trust warning when there are errors
  list.appendChild(el('div', 'flag', '⚠ Data errors present — do NOT treat remaining results as a confirmed all-clear.'));
  document.body.appendChild(list);
}}

// ─── Footer ──────────────────────────────────────────────────────────────────

function renderFooter() {{
  document.body.appendChild(el('footer', null,
    'Scout suggests. It never executes.<br>' +
    'Verify on Revolut before acting. Counsel, not a guarantee.<br>' +
    'Process over outcome. Patience. Position. Process.'
  ));
}}

// ─── Bootstrap ───────────────────────────────────────────────────────────────

renderHeader();
renderVerdict();
renderSetups();
renderWatchlist();
renderDataHealth();
renderFooter();
</script>
</body>
</html>"""
