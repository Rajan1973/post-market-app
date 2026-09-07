---
name: weekly-brief
description: >
  Generate the NIFTY & BEYOND weekly EOD post-market wrap & intelligence brief end-to-end. Compiles weekly pack from Supabase weekly_prices & weekly_indicators, fetches Tijori macro/metals & 37-stock momentum intel, authors weekly narrative prose, renders light-themed HTML report, and verifies it. Use whenever the user asks for "weekly brief", "weekly report", "weekly wrap", "weekly update", or "how did the market perform this week". Runs in d:\Anti Gravity\post-market-report.
---

# NIFTY & BEYOND — Build the Weekly Brief

**Working Directory:** `d:\Anti Gravity\post-market-report`  
**Master Guidelines:** [`reports/ag-postmarket-new-guidelines.md`](file:///d:/Anti%20Gravity/post-market-report/reports/ag-postmarket-new-guidelines.md)

This skill generates the official **NIFTY & BEYOND** weekly market wrap & intelligence brief for a target week (e.g. 31 August – 5 September 2026).

---

## 5-Step Weekly Execution Workflow

### Step 1: Autonomous Weekly Calculation Engine (Direct Supabase Query)
```powershell
python scripts/build_weekly_engine.py <YYYY-MM-DD>
```
Queries Supabase PostgreSQL database directly (`weekly_prices`, `weekly_indicators`, `fii_dii_cash_market_daily`, `daily_prices`, `index_breadth`) to calculate:
- Weekly returns & price deltas for 23 indices & commodities
- 5 Visual Cluster Performance Groups (Benchmarks, Banking/Financials, Cyclicals/Industrials, Defensives/Consumers, Commodities/FX)
- Weekly Market Regime score & component breakdown
- §3 "What's Unusual This Week" statistical anomalies & ranks
- §7 Weekly Breadth & Participation across prior weeks (This Week, Last Week, 2W Ago, 4W Ago)
- Weekly stock scanners (Top 20 Gainers & Losers) & weekly momentum composite
- Cumulative weekly FII & DII cash market flows
Generates `data/packs/weekly_calculated_<date>.json`.

### Step 2: Macro & Metals Weekly Check (Tijori + SQLite)
```powershell
python scripts/macro_check.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for 50 macro indicators + base/precious metals (Silver, Copper, Aluminium, Zinc, Steel). Updates `data/macro/macro_history.db` and exports `data/macro/macro_summary_<date>.json`.

### Step 3: Momentum Stock Enrichment (Tijori)
```powershell
python scripts/momentum_enrichment.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for all 37 momentum stocks for business overviews, operational KPIs, knowledge base updates, and announcements into `data/enrichment/momentum_enriched_<date>.json`.

### Step 4: Author Weekly Narrative Prose
1. Author weekly narrative in `reports/narrative/weekly_<date>.json`.
2. Header title: `NIFTY & BEYOND`. Tagline: `What the index doesn't tell you · Weekly Wrap · <Start Date> – <End Date>`.
3. Add `s1_summary_note` callout at end of Section 1 containing weekly overall session synthesis.
4. Follow institutional narrative rules: explicit Glosses for §2, multi-sentence anomaly cards for §3 matching candidate rank order, 3-path weekly global transmission chain (§5), derivative PCR/put-floor analysis (§13), and action plan with *Confirms if / Denies if* criteria (§14).

### Step 5: Render Weekly HTML Report & Verify
```powershell
python scripts/render_weekly_report.py <YYYY-MM-DD> --verify
```
Merges Weekly Pack + Macro Summary + Stock Intel + Weekly Narrative into `reports/rendered/<date>-weekly-brief.html` and executes automated verification checks.
