# Ingestion Pipeline & Provenance Architecture

This document describes the read-only local ingestion architecture, hashing, classification, entity resolution, and data provenance model for **NIFTY & BEYOND**.

---

## 1. System Pipeline Flow

```text
┌────────────────────────────────────────────────────────┐
│ WINDOWS LOCAL SOURCE DIRECTORIES (Read-Only)            │
│ D:\Anti Gravity\post-market-report\reports\rendered    │
│ D:\Anti Gravity\stock-reports-with-Antigravity\outputs │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 1. INVENTORY SCANNER & SHA-256 HASHING                 │
│ - Recursively scan directory                           │
│ - Calculate SHA-256 digest                             │
│ - Classify report_type (EOD / SECTOR_RESEARCH)         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. MODULAR HTML PARSER ENGINE                          │
│ - EODReportParser (DOM extraction §1..§14)             │
│ - SectorReportParser (Thesis, Scissor, Cards, Matrix)  │
│ - Generate Common Intermediate Format (JSON)           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. ENTITY RESOLUTION SERVICE                           │
│ - Match raw ticker/name against stocks & aliases       │
│ - Resolved → Attach stock_id                           │
│ - Unresolved → Route to unresolved_entities queue     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. SUPABASE DATABASE & PROVENANCE LAYER                │
│ - Store normalized records in PostgreSQL               │
│ - Attach source_locator (e.g. filename.html#s8)        │
│ - Non-blocking error logger                            │
└────────────────────────────────────────────────────────┘
```

---

## 2. Read-Only Ingestion Security
- **Strict Read-Only Enforcement**: The ingestion agent opens source HTML files using `open(path, 'r')` in read mode only. No file handles are opened with write (`'w'`), append (`'a'`), or mutation privileges against the source directories.
- **File Integrity & Hashing**: Every source file receives a 64-character hex SHA-256 digest (`source_hash`). If an identical SHA-256 hash is encountered during a future scan, ingestion is skipped to prevent duplicate database rows.

---

## 3. Data Provenance Model
Every extracted record in the database maintains exact provenance linking back to its original source location:

```sql
source_locator = '2026-09-04-daily-brief.html#s8'
```

Components of `source_locator`:
1. `source_filename`: Exact filename of authoritative source report.
2. `section_code`: DOM Section ID (`s1`..`s14`, `thesis`, `scissor`, `matrix`, `calls`).

---

## 4. Unresolved Entities Queue
When an extracted stock or sector name (e.g. `UNKNOWN_CO_XYZ`) cannot be matched with 100% confidence against the database alias dictionary:
1. It is not discarded.
2. A record is inserted into `unresolved_entities` with status `pending`.
3. The record stores candidate matches and confidence scores for review in future phases.
