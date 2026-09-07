---
name: daily-brief
description: >
  Generate the NIFTY & BEYOND daily EOD post-market brief end-to-end. Fetches the Supabase report pack, runs Tijori macro check and 20-stock momentum enrichment, researches global cues, writes the narrative, renders the light-themed HTML report, and verifies it. Use whenever the user asks for "build the report", "generate the brief", "daily brief", "EOD report", "post-market report", "market wrap", or "how did the market close today". Runs in d:\Anti Gravity\post-market-report.
---

# NIFTY & BEYOND — Build the Daily Brief

**Working Directory:** `d:\Anti Gravity\post-market-report`  
**Master Guidelines:** [`reports/ag-postmarket-new-guidelines.md`](file:///d:/Anti%20Gravity/post-market-report/reports/ag-postmarket-new-guidelines.md)

This skill generates the official **NIFTY & BEYOND** daily EOD market brief (14 sections across 4 movements + standalone *How to Read This Report* section).

---

## 5-Step Execution Workflow

### Step 0: Check Database Health
```powershell
python scripts/health_check.py
```
Verifies table fresh dates in Supabase.

### Step 1: Fetch Supabase Data Pack
```powershell
python scripts/fetch_pack.py <YYYY-MM-DD>
```
Downloads core market facts, breadth metrics, and scanners into `data/packs/<date>.json`.

### Step 2: Macro & Metals Check (Tijori + SQLite)
```powershell
python scripts/macro_check.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for 50 macro indicators + base/precious metals (Silver, Copper, Aluminium, Zinc, Steel). Updates `data/macro/macro_history.db` and exports `data/macro/macro_summary_<date>.json`.

### Step 3: 20-Stock Momentum Enrichment (Tijori)
```powershell
python scripts/momentum_enrichment.py --date <YYYY-MM-DD>
```
Queries Tijori Finance MCP for **all 20 Section 10 momentum stocks** (fresh entries + continued momentum) for business overviews, operational KPIs, knowledge base updates, and announcements into `data/enrichment/momentum_enriched_<date>.json`.

### Step 4: Author Narrative Prose & Web Cues
1. Verify target date weekday name (e.g. `2026-09-04` is a **Friday**).
2. Perform web search for US close (Dow/Nasdaq/S&P), Asian markets open, Brent crude ($), Gold spot, USD/INR.
4. Author narrative in `reports/narrative/<date>.json` (or use `python scripts/render_report.py <date> --stub`).
5. Follow institutional narrative rules: Standardized Header (`NIFTY & BEYOND` + `What the index doesn't tell you · NSE · <Weekday>, <Day> <Month> <Year>`), Executive Summary Callout (`s1_summary_note`) at end of Section 1, 6 detailed scorecard bullets (§1), non-placeholder glosses for all 5 regime inputs (§2), multi-sentence technical & structural anomaly cards for ALL candidate items (§3), 3-path global transmission chain (§5), derivative PCR/put-floor analysis (§13), and action plan with *Confirms if / Denies if* criteria (§14).

### Step 5: Render HTML Report & Verify
```powershell
python scripts/render_report.py <YYYY-MM-DD> --verify
```
Merges Pack + Macro Summary + Stock Intel + Narrative into `reports/rendered/<date>-daily-brief.html` and executes automated verification checks.

---

## Critical Execution Rules

1. **Light Theme ALWAYS**: Reports MUST be light-themed ALWAYS (`background: #FFFFFF` / `#F8FAFC`).
2. **Sort Icons**: Table headers use direct unicode arrow glyphs (` ↕`, ` ↑`, ` ↓`). Never use octal string escapes (`\2195`) inside Python CSS strings.
3. **Day-of-Week Date Verification**: Always verify the weekday of the target date before writing prose.
4. **Standalone How to Read Section**: Standalone final section rendered after Section 14 with Georgia serif typography and 6-card methodology guide.
5. **Institutional Narrative Depth**: Every anomaly in §3 must explain *market mechanics* (e.g. de-rating of future earnings multiples vs. immediate earnings impact, volume-price divergence, VIX vs geopolitical risk tension).
6. **No Kite / Tapetide**: Kite MCP / tapetide are retired; all financial & macro intel is powered by Supabase, Tijori MCP, and web search.
