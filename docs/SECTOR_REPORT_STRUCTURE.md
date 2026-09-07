# Sector Report HTML Structure & CSS Selectors

This document records the exact HTML hierarchy and CSS selectors discovered during inspection of the **Rajan Sector Earnings Review Reports** located at `D:\Anti Gravity\stock-reports-with-Antigravity\outputs`.

---

## 1. Header & Metadata Selectors

| Entity | Selector | Example Value / HTML Snippet |
| :--- | :--- | :--- |
| **Eyebrow** | `.eyebrow` | `RAJAN SECTOR EARNINGS REVIEW • Q1 FY27 • SECTOR #9` |
| **Sector H1** | `h1` | `01 / METALS & MINING` |
| **Sector Name** | Parsed from `h1` | `METALS & MINING` |
| **Period** | Parsed from `.eyebrow` | `Q1 FY27` |

---

## 2. Component Structures

### A. Sector Thesis & Synthesis
- **Selector**: `.synth`
- **Content**: Paragraphs (`p`) detailing sector narrative, drivers, valuation environment, and earnings trajectory.

### B. Scissor Analysis (Revenue Growth vs Margin Change)
- **Container**: `.scissor`
- **Legend**: `.legend span`
- **Company Row**: `.row`
- **Company Name**: `.row .co`
- **Bar Track**: `.track`
- **Volume / Growth Bar**: `.b.v`
- **Margin Expansion / Compression Bar**: `.b.e.pos`, `.b.e.neg`

### C. Company Cards (`.grid .c`)
- **Container Grid**: `.grid`
- **Company Card**: `.c`
- **Logo / Ticker**: `.logo .mono`
- **Guidance Delivery Badge**: `.badge.del` (Delivered), `.badge.part` (Partial), `.badge.miss` (Missed)
- **Metric Tiles Grid**: `.tiles`
- **Metric Tile**: `.tile` (`.n` for value, `.l` for label e.g. `OPM 16.4%`)
- **Key Observation Bullets**: `ul li`
- **Flag Tags**: `.flag.ok` (Positive), `.flag` (Red flag / risk)

### D. Beat / Miss Matrix
- **Container**: `.matrix`
- **Table**: `table`
- **Headers**: `th` (Company, Revenue, EBITDA, PAT, Margin Δ)
- **Data Rows**: `tr`

### E. Management Quotes & Guidance
- **Container**: `.quotes`
- **Quote Card**: `.qcard`
- **Quote Text**: `blockquote`
- **Speaker Name**: `.auth`
- **Speaker Role**: `.role`

### F. Guidance Delivery Scorecards
- **Container**: `.wtgrid`
- **Scorecard**: `.wtcard`
- **Score Badge**: `.wtscore.high`, `.wtscore.mid`

### G. Valuation Calls
- **Container**: `.calls`
- **Call Card**: `.call.buy`, `.call.hold`, `.call.watch`
- **Rating**: `.type` (BUY, HOLD, WATCHLIST)
- **Stock Target**: `h3`, `.target`
- **Rationale**: `p`
