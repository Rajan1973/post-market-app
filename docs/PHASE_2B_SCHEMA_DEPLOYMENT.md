# NIFTY & BEYOND — Phase 2B Schema Deployment & Pilot Preparation Report

## 1. Target Database Verification

* **Expected Project Reference:** `post-market-app`
* **Configured Connection Host:** `aws-0-ap-south-1.pooler.supabase.com`
* **Extracted Connection Project Ref:** `wtbufledttydooazwiuw`
* **Target Project Identity:** `nifty500data` (Market Data Warehouse Project)
* **Verification Status:** **HALTED — PROJECT REF MISMATCH & TARGET IS NIFTY500DATA**

> [!WARNING]
> **Safety Guard Triggered:** The configured `DATABASE_URL` in `.env` points to Supabase project `wtbufledttydooazwiuw`, which houses the existing `nifty500data` market database (containing `daily_prices`, `weekly_prices`, `index_breadth`, `rrg_*` tables).
>
> In accordance with Phase 2B Safety Rules 1 & 2, schema migration to `wtbufledttydooazwiuw` was **HALTED IMMEDIATELY** to prevent deploying the research schema into the separate `nifty500data` project.

---

## 2. Migration Status & Audit

* **Migration Safety Inspector:** `supabase/check_migrations.py`
* **Inspection Verdict:** **PASS** (4 migration files, 17 tables declared, 0 destructive SQL queries)
* **Deployment Status:** **HELD** (Pending provision/configuration of dedicated `post-market-app` research database connection)

### Migration Sequence:

1. `supabase/migrations/001_initial_schema.sql` (Tables: `reports`, `report_sections`)
2. `supabase/migrations/002_entity_tables.sql` (Tables: `sectors`, `stocks`, `themes`, `entity_aliases`, `report_mentions`, `entity_relationships`, `unresolved_entities`)
3. `supabase/migrations/003_metrics_tables.sql` (Tables: `market_metrics`, `stock_metrics`, `sector_metrics`, `sector_flexible_metrics`, `sector_rotation`, `research_events`)
4. `supabase/migrations/004_signals_tables.sql` (Tables: `signals`, `signal_evidence`)

---

## 3. Schema & Row Count Status

* **Target Research Database:** Not deployed (held due to target mismatch).
* **Expected Tables (17):**
  * `reports` (0 rows)
  * `report_sections` (0 rows)
  * `stocks` (0 rows)
  * `sectors` (0 rows)
  * `themes` (0 rows)
  * `entity_aliases` (0 rows)
  * `report_mentions` (0 rows)
  * `entity_relationships` (0 rows)
  * `unresolved_entities` (0 rows)
  * `market_metrics` (0 rows)
  * `stock_metrics` (0 rows)
  * `sector_metrics` (0 rows)
  * `sector_flexible_metrics` (0 rows)
  * `sector_rotation` (0 rows)
  * `research_events` (0 rows)
  * `signals` (0 rows)
  * `signal_evidence` (0 rows)

---

## 4. Pilot Manifest (`reports/pilot/PHASE_2B_PILOT_MANIFEST.json`)

The 7-report pilot manifest has been generated with exact SHA-256 digests and file metadata:

| Report Type | File | SHA-256 Digest | Size (bytes) | Report Date |
| :--- | :--- | :--- | :---: | :---: |
| **EOD Daily** | `2026-09-04-daily-brief.html` | `78458818cd11a64bb64912ae044129d23597ea4c8e5396d20413515f3df38d0c` | 100,770 | 2026-09-04 |
| **EOD Daily** | `2026-09-03-daily-brief.html` | `64b915b23aa7b578b2a396044c1c53a44a27d788c8f4568aee586ea24f49a341` | 102,035 | 2026-09-03 |
| **EOD Daily** | `2026-09-01-daily-brief.html` | `046db4d64df63a2cc8c730082869bf64057107fac8327b2204919cc9cdc063dd` | 91,561 | 2026-09-01 |
| **EOD Weekly** | `2026-09-04-weekly-brief.html` | `9f178d0581c946d647f7b721522bb81cfc6f8d23b75eb99ff3029e9fc5955925` | 107,822 | 2026-09-04 |
| **Sector Research** | `metals-mining-q1fy27-sector-review.html` | `2b29d78f4c5b9338a6dffabd39db7a5adb489c555cec9377482e262cf7d6cc54` | 39,896 | 2026-09-04 |
| **Sector Research** | `gold-jewellery-q1fy27-sector-review.html` | `4a4ede16a22b7c44152ae3e5dfb34b3f8455ec006146244c04ff1f791a88b1a1` | 34,828 | 2026-09-04 |
| **Sector Research** | `power-generation-q1fy27-sector-review.html` | `9c9d62c4fa270835200a4b1ab268dc88aa7b4cecaad86db210f6c41948d4d691` | 36,988 | 2026-09-04 |

---

## 5. Canonical Database Ingestion Path

* **Canonical Connection:** `PostgreSQL` via `psycopg2` using connection pooling or direct connection strings from `config/settings.py`.
* **Canonical Write Method:** Relational transactional inserts with ON CONFLICT / upsert semantics across primary keys (`reports.sha256`, `stocks.symbol`, `sectors.name`).
* **Authentication Mechanism:** Supabase PostgreSQL credentials via `DATABASE_URL`.
* **Production Safety Checks:**
  1. `PRODUCTION_INGEST_ENABLED` must be explicitly set to `true`.
  2. `EXPECTED_PROJECT_REF` must match `post-market-app`.
  3. Connection target must not contain `nifty500data` tables.
  4. Manifest validation (exact 7 report hash verification).

---

## 6. Pilot Ingestion Command (NOT YET EXECUTED)

```bash
python -m ingestion.pipeline --manifest reports/pilot/PHASE_2B_PILOT_MANIFEST.json
```

> [!IMPORTANT]
> **Execution Status:** **NOT EXECUTED.** Per Phase 2B critical stop condition, pilot ingestion command has been configured and tested in dry-run mode only. Execution awaits user approval and target database URL update.
