# Data Dictionary

Formal data dictionary for all normalized extracted fields, database columns, and intermediate JSON data structures in **NIFTY & BEYOND**.

---

## 1. Core Metadata Fields (`reports` table)

| Field Name | Type | Meaning / Description | Source | Example |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key | Generator | `a1b2c3d4-0000-0000-0000-000000000001` |
| `report_type` | String | Classification: `EOD`, `SECTOR_RESEARCH`, `UNKNOWN` | Classifier | `EOD` |
| `title` | String | Main title of the report document | HTML `h1` | `NIFTY & BEYOND` |
| `report_date` | Date | Publication date in YYYY-MM-DD | Subtitle / Filename | `2026-09-04` |
| `source_filename` | String | Original filename | File system | `2026-09-04-daily-brief.html` |
| `source_hash` | String | SHA-256 digest for auditability and de-duplication | File system | `78458818cd11a64bb64912ae...` |
| `headline` | Text | Executive summary callout text | `.callout` | `The Sensex snapped a four-day...` |

---

## 2. Market & Stock Metric Fields (`stock_metrics` & `market_metrics`)

| Field Name | Type | Meaning / Description | Source | Unit | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ltp` | Numeric | Last Traded Price | Scanner Table | INR (₹) | `1380.05` |
| `daily_return` | Numeric | Single day percentage price change | Scorecard / Table | % | `+0.10` |
| `volume_x14` | Numeric | Current volume relative to 14-day average volume | Stock Scanner | Multiple (×) | `6.77` |
| `volume_x63` | Numeric | Current volume relative to 63-day average volume | Stock Scanner | Multiple (×) | `5.50` |
| `rsi14` | Numeric | 14-period Relative Strength Index | Stock Scanner | Index (0-100) | `78.70` |
| `adx14` | Numeric | 14-period Average Directional Index (Trend strength) | Stock Scanner | Index (0-100) | `39.60` |
| `pct_from_20sma` | Numeric | Percentage distance from 20-day SMA | Stock Scanner | % | `+22.60` |

---

## 3. Sector & Breadth Fields (`sector_metrics` & `sector_rotation`)

| Field Name | Type | Meaning / Description | Source | Unit | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ad_ratio` | Numeric | Advance to Decline ratio (Advances / Declines) | §7 Breadth Table | Ratio | `0.88` |
| `pct_above_20dma` | Numeric | Percentage of index constituent stocks above 20-day SMA | §7 Breadth Table | % | `42.4` |
| `direction` | String | Rotation direction: `rotating_in`, `rotating_out`, `neutral` | §8 Rotation | Enum | `rotating_in` |

---

## 4. Sector Financial & Scissor Fields (`sector_flexible_metrics`)

| Field Name | Type | Meaning / Description | Source | Example |
| :--- | :--- | :--- | :--- | :--- |
| `guidance_delivery` | String | Management guidance track record: `DELIVERED`, `PARTIAL`, `MISSED` | Company Card Badge | `DELIVERED` |
| `opm` | Numeric | Operating Profit Margin | Metric Tile | `16.4%` |
| `realization` | Numeric | Product realization metric (e.g. Cables/sqft realization) | Tijori Feed | `₹12,915/sqft` |
