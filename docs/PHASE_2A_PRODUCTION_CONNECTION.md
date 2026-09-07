# Phase 2A — Production Connection Preparation Document

**System**: NIFTY & BEYOND Research Intelligence Platform  
**Phase**: Phase 2A (Pre-Production Connection Preparation)  
**Date**: 2026-09-07  
**Repository**: `Rajan1973/post-market-app`  

---

## 1. Required Environment Variables

The following environment variable names are required for production database connectivity. **Secret values must NEVER be committed to Git.**

| Variable Name | Purpose | Default / Example Value |
| :--- | :--- | :--- |
| `PRODUCTION_INGEST_ENABLED` | **Safety Switch**: Must be `true` to allow DB writes | `false` |
| `EXPECTED_PROJECT_REF` | Target Supabase project reference | `post-market-app` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres.[REF]:[PASS]@...:5432/postgres` |
| `SUPABASE_URL` | Supabase REST API URL | `https://[REF].supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase Anonymous Client Key | Client API Key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role Key (Backend Ingestion Only) | Service Role Key |
| `EOD_REPORT_PATH` | Local read-only directory path for EOD reports | `D:\Anti Gravity\post-market-report\reports\rendered` |
| `SECTOR_REPORT_PATH` | Local read-only directory path for Sector reports | `D:\Anti Gravity\stock-reports-with-Antigravity\outputs` |

---

## 2. Database Architecture & Coexistence

- **`nifty500data` (Existing Market Data Warehouse)**:
  - Contains daily OHLCV prices, technical indicators, and market flows (`daily_prices`, `daily_indicators`, `index_breadth`, `fii_daily_flows`, `dii_daily_flows`).
  - **Is NOT modified or migrated** by this repository.
- **`post-market-app` (NIFTY & BEYOND Research Intelligence)**:
  - Contains the research graph (`reports`, `report_sections`, `market_metrics`, `sector_flexible_metrics`, `research_events`, `signals`, `signal_evidence`, `entity_relationships`).
  - Cross-references market warehouse data via `symbol` and `metric_date` without physically duplicating price series.

---

## 3. Production Safety Mechanism

A dual-lock safety mechanism prevents accidental production database writes:

1. **`PRODUCTION_INGEST_ENABLED` Safety Switch**:
   - Implemented in `config/settings.py`.
   - Defaults to `false`.
   - Ingestion pipeline scripts verify `PRODUCTION_INGEST_ENABLED == True` before attempting any database INSERT or UPSERT operations.
2. **Project Reference Verification (`EXPECTED_PROJECT_REF`)**:
   - Verifies that target URL / project reference matches `EXPECTED_PROJECT_REF` to prevent writing to the wrong Supabase instance.
3. **Destructive Query Protection**:
   - Zero `DROP TABLE`, `TRUNCATE TABLE`, or `DELETE FROM` statements exist in migrations or ingestion code.
   - Database operations use idempotent `INSERT` / `UPSERT` with mandatory SHA-256 duplicate checking.

---

## 4. Migration Status

- **Migration Directory**: `supabase/migrations/`
- **Migration Scripts**:
  - `001_initial_schema.sql` (Version 001: Core `reports` and `report_sections`)
  - `002_entity_tables.sql` (Version 002: Core entities, mentions, `entity_relationships`, `unresolved_entities`)
  - `003_metrics_tables.sql` (Version 003: `market_metrics`, `stock_metrics`, `sector_metrics`, `sector_flexible_metrics`, `sector_rotation`, `research_events`)
  - `004_signals_tables.sql` (Version 004: `signals`, `signal_evidence`)
- **Status**: **NOT YET APPLIED** to production Supabase database. Scripts are prepared locally.

---

## 5. Non-Destructive Connectivity Check Command

To verify database reachability and table existence without inserting, updating, deleting, or altering data, run:

```bash
python -m ingestion.connection_check
```

### What It Verifies:
1. Checks that `PRODUCTION_INGEST_ENABLED` state is explicitly reported.
2. Performs a read-only PostgreSQL version query (`SELECT version();`).
3. Queries `information_schema.tables` in read-only mode to report which required tables exist and which are pending deployment.

---

## 6. Expected Connectivity Check Result

When run against a configured, migrated database, `ingestion/connection_check.py` will report:

```json
{
  "status": "CONNECTED",
  "db_version": "PostgreSQL 15.1...",
  "production_ingest_enabled": false,
  "existing_tables_count": 17,
  "required_tables_found": 17,
  "missing_tables": []
}
```

---

## 7. Remaining Risks & Mitigations

1. **Unapplied Migrations**: Target database requires executing `supabase/migrations/*.sql` before initial ingestion.
   - *Mitigation*: Run connectivity check script prior to ingestion to verify table presence.
2. **Environment Secret Leakage**: Accidental check-in of `.env`.
   - *Mitigation*: `.gitignore` explicitly ignores `.env` files. Template provided in `.env.example`.
