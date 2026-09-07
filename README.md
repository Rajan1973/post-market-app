# NIFTY & BEYOND — Post-Market Intelligence Report Generator

Report generation workspace for the daily EOD post-market brief.
All report code, scripts, and macro storage live here. The upstream database (`github.com/rajanchennai/market-data`) is **read-only**.

Full operating specifications and architecture rules: [`reports/ag-postmarket-new-guidelines.md`](file:///d:/Anti%20Gravity/post-market-report/reports/ag-postmarket-new-guidelines.md).

---

## Architecture & Data Flow

```
┌──────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐
│  Supabase Pack   │  │   Tijori Finance MCP  │  │ SQLite Macro Store  │
│ (Read-only SQL)  │  │ (Node.js JSON-RPC 2.0)│  │ (data/macro_history)│
└────────┬─────────┘  └───────────┬───────────┘  └──────────┬──────────┘
         │                        │                         │
         ▼                        ▼                         ▼
  fetch_pack.py             tijori_client.py           macro_check.py
  (data/packs/)            (Stock/Sector Intel)      (50 Macro Indicators)
         │                        │                         │
         └────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                        momentum_enrichment.py
                       (Enriches All 20 Stocks)
                                  │
                                  ▼
                           render_report.py
                 (HTML Report + How to Read Section)
```

---

## Core Execution Pipeline

### Step 0 — Check Database Health
```powershell
python scripts/health_check.py
```
Validates connection to Supabase and verifies table fresh timestamps.

### Step 1 — Fetch the Data Pack
```powershell
python scripts/fetch_pack.py <YYYY-MM-DD> --force
```
Extracts all core facts, breadth ratios, sector momentum, and scanners into `data/packs/<date>.json`.

### Step 2 — Run Macro & Metals Check (Tijori + SQLite)
```powershell
python scripts/macro_check.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for base/precious metals and 50 macroeconomic indicators, populates SQLite (`data/macro/macro_history.db`), and exports `data/macro/macro_summary_<date>.json`.

### Step 3 — Run Momentum Stock Enrichment (All 20 Stocks)
```powershell
python scripts/momentum_enrichment.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for all 20 Section 10 momentum stocks (fresh entries + continued momentum) for business overviews, operational KPIs, knowledge base updates, and announcements. Exports `data/enrichment/momentum_enriched_<date>.json`.

### Step 4 — Author Institutional Narrative & Web Cues
Author narrative prose in `reports/narrative/<date>.json` (or generate a skeleton using `python scripts/render_report.py <date> --stub`).

### Step 5 — Render HTML & Verify
```powershell
python scripts/render_report.py <YYYY-MM-DD> --verify
```
Merges Pack + Macro Summary + Stock Intel + Narrative into `reports/rendered/<date>-daily-brief.html` and executes automated verification checks.

---

## Directory Structure

```
d:\Anti Gravity\post-market-report\
├── reports\
│   ├── ag-postmarket-new-guidelines.md  <-- Master Guidelines Document
│   ├── narrative\                       <date>.json — prose written at report time
│   └── rendered\                        <date>-daily-brief.html — output HTML
├── data\
│   ├── packs\                           <date>.json — pack cached from Supabase
│   ├── macro\                           macro_summary_<date>.json & macro_history.db
│   └── enrichment\                      momentum_enriched_<date>.json
├── scripts\
│   ├── fetch_pack.py                    Supabase pack downloader
│   ├── tijori_client.py                 Python ↔ Tijori Node.js MCP bridge
│   ├── macro_check.py                   Macro & metal price fetcher (SQLite)
│   ├── momentum_enrichment.py           Tijori stock intel fetcher (All 20 stocks)
│   ├── health_check.py                  Database fresh check
│   └── render_report.py                 HTML Report Builder
└── .env                                 DATABASE_URL (gitignored)
```

---

## Active Guidelines & Rules

1. **Light Theme Always**: Reports MUST be light-themed ALWAYS (`#FFFFFF` / `#F8FAFC`).
2. **Sort Icons**: Table headers use direct unicode arrow glyphs (` ↕`, ` ↑`, ` ↓`).
3. **Standardized Header Format**: Title `NIFTY & BEYOND`, Tagline `What the index doesn't tell you · NSE · <Weekday>, <Day> <Month> <Year>`.
4. **Executive Summary Callout**: Synthesis callout paragraph placed at the end of Section 1 (`s1_summary_note`).
5. **Tijori Operational Intel**: Integrate Tijori operational metrics (RevPAR, sqft realization, order book % of sales, sugar recovery, ANDA filings) into Section 3 & Section 10 cards.
6. **Complete Narrative Depth**: Plain-English glosses for Section 2, 3-path global transmission chain for Section 5, derivative PCR/Put-floor analysis for Section 13, and Confirms/Denies criteria for Section 14.
