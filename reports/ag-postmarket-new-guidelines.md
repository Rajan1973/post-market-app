# NIFTY & BEYOND — Post-Market Report Generation Guidelines & Architecture

**Document Version:** 2.5 (Updated September 2026)  
**Status:** Active Operating Standard  
**Framework Spec:** `reports/daily-market-brief-framework-31Aug-2026.md`

---

## 1. Executive Overview & Core Principle

**NIFTY & BEYOND** is the single merged daily EOD post-market intelligence report for Indian equities (NSE). It synthesizes 14 core sections into four distinct movements, followed by an instructional methodology guide (*How to Read This Report*).

### The Golden Rule
> **The Data Pack carries facts. AI / Report Writer writes judgement.**
> The data pipeline computes numbers, percentages, ranks, deltas, and statistical flags. Every narrative bullet and headline sentence is generated at report time using empirical facts from the pack, Tijori Finance intel, and verified web search.

---

## 2. Core Architecture & Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA SOURCES & BRIDGES                          │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│    Supabase EOD Pack     │   Tijori Finance MCP     │   SQLite Macro Store  │
│  (Read-only DB tables)   │ (Node.js JSON-RPC 2.0)   │ (data/macro_history)  │
└────────────┬─────────────┴────────────┬─────────────┴───────────┬───────────┘
             │                          │                         │
             ▼                          ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AUTOMATED ENRICHMENT PIPELINE                      │
│                                                                             │
│  1. fetch_pack.py  ──> data/packs/<date>.json                               │
│  2. macro_check.py ──> data/macro/macro_summary_<date>.json & SQLite DB     │
│  3. momentum_enrichment.py ──> data/enrichment/momentum_enriched_<date>.json│
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REPORT GENERATION & RENDERING                       │
│                                                                             │
│  render_report.py  ──> Merges Pack + Macro Summary + Stock Intel + Narrative│
│                    ──> Outputs: reports/rendered/<date>-daily-brief.html    │
└────────────────────────────────────────┬────────────────────────────────────┘
```

---

## 3. Section-by-Section Data & Formatting Specification

The report consists of **14 numbered sections across 4 movements**, followed by a standalone **How to Read This Report** methodology section:

| Movement | Section | Title | Primary Data Source |
|---|---|---|---|
| **A. The Read** | **§1** | Executive Scorecard | Pack (Equities/Flows) + Tijori Metals & Web Global Prices |
| | **§2** | Market Regime | Pack (`s2_regime` score & component weights) |
| | **§3** | What's Unusual Today | Pack (`s3_unusual` candidates ranked by percentile) |
| **B. The Context** | **§4** | Macro & Policy Dashboard | Tijori Macro Feed (`get_macro_indicators`) + Web Search |
| | **§5** | Global Cues, Currency & Commodities | Web Search (US markets, Asian markets, Brent, Gold, USD/INR) |
| **C. The Structure**| **§6** | Index Market Structure | Pack (`s6_structure` 6a board & 6b sector bars) |
| | **§7** | Breadth & Participation | Pack (`s7_breadth` A/D and % >20D SMA table + crosslinks) |
| | **§8** | Sector Rotation | Pack (`s8_rotation` 5-session & 1-month participation deltas) |
| | **§9** | Stock Scanners | Pack (`s9_scanners` top gainers & top losers) |
| | **§10**| Momentum Scanners | Pack (`s10_momentum`) + Tijori Stock Intel (All 20 stocks enriched) |
| | **§11**| FII / DII Flows | Pack (`s11_flows` cash market net buying/selling & windows) |
| **D. The Forward View**| **§12**| What Changed Today | Pack (`s12_changed` regime & breadth deltas) |
| | **§13**| Futures, Options & Expiry | Pack + Web (PCR, Max Pain, Crossover Strike, Scenario analysis) |
| | **§14**| Tomorrow's Action Plan | Narrative triggers (Bull/Bear triggers, Watch items, Events) |
| **Methodology** | **Final** | **How to Read This Report** | Standalone instruction section (6-card methodology guide) |

---

## 4. Institutional Narrative Writing Standards & Analytical Depth

To match institutional-grade quality, the narrative JSON (`reports/narrative/<date>.json`) must strictly adhere to the following 7 principles:

1. **Standardized Header Format & Executive Summary Synthesis Callout**:
   - Header Title (`<h1>`): Always `NIFTY & BEYOND`.
   - Header Tagline (`.sub`): Always `What the index doesn't tell you · NSE · <Weekday>, <Day> <Month> <Year>` (e.g., *What the index doesn't tell you · NSE · Friday, 4 September 2026*).
   - Executive Summary Callout (`s1_summary_note`): The multi-sentence overall session synthesis narrative paragraph is placed at the end of Section 1 (Executive Scorecard) as a highlighted summary callout block.

2. **Executive Scorecard Bullets (§1)**:
   - Provide 6 rich, storytelling bullets covering Index, Breadth, Institutional Flows, Standout News/Catalyst, Global Cues, and Volatility (India VIX).

3. **Plain-English Regime Component Glosses (§2)**:
   - Provide explicit, non-placeholder glosses for all 5 regime components (Breadth, Trend, Momentum, Institutional Flow, Volatility).
   - Write a detailed composition callout explaining the spread between the strongest and weakest components and what happens when Volatility is excluded.

4. **Multi-Sentence Deep Anomaly Cards (§3)**:
   - Must match ALL candidates provided in `s3_unusual` in the exact pack order.
   - Include specific technical metrics (`% above/below 20SMA`, `RSI-14`, `ADX-14`, `Volume x63`), corporate catalysts, and structural readings (e.g. de-rating of future earnings multiples vs. immediate earnings impact).

5. **Explicit 3-Path Global Transmission Chain (§5)**:
   - Explain how global events traveled into Indian markets across 3 distinct paths: (1) Open & Futures, (2) Currency & Reserves, (3) Safe Havens (Gold/Silver).
   - Explicitly highlight where the global transmission *failed* to reach (domestic sector breadth).

6. **Derivative & Expiry Structural Read (§13)**:
   - Detail PCR shifts, Put Floor migration (e.g., writers moving defensive lines up to ATM), Call Wall resistance, and futures short-covering / long-buildup dynamics.

7. **Structured Action Plan with Confirms/Denies Criteria (§14)**:
   - Provide 6 watch items, each with concrete *Confirms if* and *Denies if* validation tests.
   - Include an upcoming dated event calendar, Bull/Bear triggers, and a concluding master synthesis callout.

---

## 5. Visual Styling & Presentation Rules

1. **LIGHT THEME ALWAYS**:
   * Reports MUST be light-themed ALWAYS (`background: #FFFFFF` / `#F8FAFC`, dark text `#0F172A`, slate borders `#E2E8F0`). Dark mode reports are forbidden.
2. **Table Header Sort Icons**:
   * All sortable table headers (`<th data-s>`) use direct unicode arrow glyphs: `content: " ↕"` (default), `content: " ↑"` (asc), `content: " ↓"` (desc). Never use octal string escapes (`\2195`) inside Python CSS strings.
3. **Day-of-Week Date Verification**:
   * Always verify the day of the week for the target date before rendering (e.g. `2026-09-04` is a **Friday**). Ensure narrative prose (`standfirst`, closing bullets) references the correct weekday name.
4. **Standalone How to Read Section**:
   * Rendered after Section 14 as a standalone `<section id="how-to-read" class="htr-section">`.
   * Features a blue left accent border (`border-left: 5px solid #2563EB`), Georgia Serif header and lead quote, and 6 step cards with font size reduced by 3px (`.htr-title`: `0.78rem`, `.htr-body`: `0.68rem`).

---

## 6. End-to-End Execution Workflow

To generate a complete EOD Post-Market Brief for a target date (e.g., `2026-09-04`):

```bash
# Step 1: Fetch Supabase Data Pack
python scripts/fetch_pack.py 2026-09-04

# Step 2: Run Macro & Metals Check (Tijori + SQLite)
python scripts/macro_check.py --date 2026-09-04

# Step 3: Run Momentum Stock Enrichment (All 20 Stocks)
python scripts/momentum_enrichment.py --date 2026-09-04

# Step 4: Write Institutional Narrative Prose (reports/narrative/2026-09-04.json)

# Step 5: Render HTML Report & Verify
python scripts/render_report.py 2026-09-04 --verify
```
*Output:* `reports/rendered/2026-09-04-daily-brief.html`
