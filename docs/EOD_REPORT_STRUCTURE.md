# EOD Report HTML Structure & CSS Selectors

This document records the exact HTML hierarchy and CSS selectors discovered during inspection of the **NIFTY & BEYOND Daily EOD Reports** located at `D:\Anti Gravity\post-market-report\reports\rendered`.

---

## 1. Document & Metadata Selectors

| Entity | Selector | Example Value / HTML Snippet |
| :--- | :--- | :--- |
| **Title** | `h1` | `NIFTY & BEYOND` |
| **Subtitle / Date** | `.mast .sub` | `What the index doesn't tell you · NSE · Friday, 4 September 2026` |
| **Callout / Lead Headline** | `.callout` | `The Sensex snapped a four-day losing streak with a 363-point gain...` |
| **Top Bar Date Stamp** | `.topbar .mono` | `2026-09-04 — close 15:30 IST — Supabase pack v1.0 + Tijori + web` |
| **PDF Download Button** | `.pdfbtn` | `Download as PDF` |

---

## 2. Navigation & Section Hierarchy (§1 to §14)

Navigation links in `nav .wrap a` map directly to `<section id="s1">` through `<section id="s14">`:

| Section ID | Section Title | Group | CSS Selector |
| :--- | :--- | :--- | :--- |
| `#s1` | §1 Executive Scorecard | **A** | `section#s1` |
| `#s2` | §2 Market Regime | **A** | `section#s2` |
| `#s3` | §3 What's Unusual Today | **A** | `section#s3` |
| `#s4` | §4 Macro & Policy Dashboard | **B** | `section#s4` |
| `#s5` | §5 Global Cues, Currency & Commodities | **B** | `section#s5` |
| `#s6` | §6 Index Market Structure | **C** | `section#s6` |
| `#s7` | §7 Breadth & Participation | **C** | `section#s7` |
| `#s8` | §8 Sector Rotation | **C** | `section#s8` |
| `#s9` | §9 Stock Scanners | **C** | `section#s9` |
| `#s10` | §10 Momentum & Extreme RSI | **C** | `section#s10` |
| `#s11` | §11 Institutional Flows | **C** | `section#s11` |
| `#s12` | §12 Changed Observations | **D** | `section#s12` |
| `#s13` | §13 F&O Market Structure | **D** | `section#s13` |
| `#s14` | §14 Trading Plan | **D** | `section#s14` |

---

## 3. Component Selectors

### A. Executive Scorecard Tiles (`section#s1`)
- **Grid Container**: `.score`
- **Tile Element**: `.tile`
- **Metric Key**: `.k` (e.g. `Nifty 50`, `FII net · cash`, `Breadth · N500`)
- **Metric Value**: `.v` (e.g. `23,897.70`, `-3,112.00`)
- **Direction / Delta**: `.d.up`, `.d.dn`

### B. Tables (Index, Breadth, Global, Flows, F&O)
- **Table Wrapper**: `.twrap`
- **Table**: `table`
- **Header Cells**: `thead th`
- **Data Cells**: `tbody td`
- **Symbol / Name**: `td.sym`
- **Numeric Cells**: `td.num`
- **Positive / Negative Formatting**: `.up` (green), `.dn` (red), `.fl` (neutral)

### C. Narrative & Observation Bullets
- **Bullet Container**: `ul.bul.narr`
- **Bullet Items**: `li`
- **Bold Keyword**: `b`
- **Pills**: `.pill.up`, `.pill.dn`, `.pill.wn`
