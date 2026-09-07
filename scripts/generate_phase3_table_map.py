"""
generate_phase3_table_map.py
Generates PHASE_3_TABLE_MAP.csv mapping all 26 tables/views in nifty500data.
"""

import csv
import json
import os

TABLE_MAPPINGS = [
    {
        "schema": "extensions",
        "table_name": "pg_stat_statements",
        "purpose": "PostgreSQL query execution performance metrics view",
        "primary_key": "NONE",
        "date_column": "N/A",
        "symbol_column": "N/A",
        "universe_role": "SYSTEM",
        "authoritative_domain": "Database Diagnostics",
        "used_by_rrg": "NO",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Postgres internal extension view"
    },
    {
        "schema": "extensions",
        "table_name": "pg_stat_statements_info",
        "purpose": "PostgreSQL query statistics metadata view",
        "primary_key": "NONE",
        "date_column": "N/A",
        "symbol_column": "N/A",
        "universe_role": "SYSTEM",
        "authoritative_domain": "Database Diagnostics",
        "used_by_rrg": "NO",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Postgres internal extension view"
    },
    {
        "schema": "public",
        "table_name": "current_index_members",
        "purpose": "View joining index_membership and instruments to present current constituent stock lists with weights",
        "primary_key": "NONE (VIEW)",
        "date_column": "effective_date",
        "symbol_column": "index_symbol, stock_symbol",
        "universe_role": "INDEX_MEMBERSHIP_VIEW",
        "authoritative_domain": "Universe / Index Constituents",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "FK target / lookup for Stock-to-Index research mapping",
        "notes": "Convenience view over index_membership & instruments"
    },
    {
        "schema": "public",
        "table_name": "daily_indicators",
        "purpose": "Daily technical indicator values (RSI_14, ATR_14, ADX_14, SMA_20/50/200, EMA_20/50/200)",
        "primary_key": "instrument_id, date",
        "date_column": "date",
        "symbol_column": "instrument_id",
        "universe_role": "QUANTITATIVE_INDICATORS",
        "authoritative_domain": "Daily Technical Indicators",
        "used_by_rrg": "NO",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only quantitative input for research signals & daily wrap",
        "notes": "Contains pre-calculated daily TA indicators for Nifty 500 stocks"
    },
    {
        "schema": "public",
        "table_name": "daily_price_indicators",
        "purpose": "View combining daily_prices and daily_indicators with instrument symbol and name",
        "primary_key": "NONE (VIEW)",
        "date_column": "date",
        "symbol_column": "symbol, instrument_id",
        "universe_role": "QUANTITATIVE_COMBINED_VIEW",
        "authoritative_domain": "Daily Price & Indicator Analytics",
        "used_by_rrg": "NO",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Primary read-only analytics view for research report generation",
        "notes": "Simplifies daily query joins for EOD briefs"
    },
    {
        "schema": "public",
        "table_name": "daily_prices",
        "purpose": "Authoritative daily OHLCV price series for all tracked instruments",
        "primary_key": "instrument_id, date",
        "date_column": "date",
        "symbol_column": "instrument_id",
        "universe_role": "QUANTITATIVE_PRICES",
        "authoritative_domain": "Daily Market Prices (OHLCV)",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Primary price reference for research valuation & performance context",
        "notes": "Daily stock & index price database"
    },
    {
        "schema": "public",
        "table_name": "data_coverage_log",
        "purpose": "Pipeline data load execution & validation audit log",
        "primary_key": "trade_date, stage",
        "date_column": "trade_date, logged_at",
        "symbol_column": "NONE",
        "universe_role": "PIPELINE_AUDIT",
        "authoritative_domain": "Data Pipeline Governance",
        "used_by_rrg": "NO",
        "used_by_eod": "NO",
        "proposed_research_dependency": "Read-only pipeline health verification",
        "notes": "Tracks pipeline ingestion completeness by stage"
    },
    {
        "schema": "public",
        "table_name": "fii_dii_cash_market_daily",
        "purpose": "Institutional investor flow data (FII & DII daily buy, sell, net values in INR Cr)",
        "primary_key": "date",
        "date_column": "date",
        "symbol_column": "NONE",
        "universe_role": "MACRO_FLOWS",
        "authoritative_domain": "Institutional Flow Data",
        "used_by_rrg": "NO",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only source for EOD macro/institutional commentary",
        "notes": "Daily FII/DII net equity activity"
    },
    {
        "schema": "public",
        "table_name": "index_breadth",
        "purpose": "Index-level market breadth metrics (advances, declines, unchanged, % > 20/50/200 DMA)",
        "primary_key": "index_name, date",
        "date_column": "date",
        "symbol_column": "index_name",
        "universe_role": "MARKET_BREADTH",
        "authoritative_domain": "Market Breadth Analytics",
        "used_by_rrg": "NO",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only input for EOD Market Pulse & Regime assessment",
        "notes": "Covers Nifty 500, Nifty 50, Midcap, Smallcap breadth"
    },
    {
        "schema": "public",
        "table_name": "index_membership",
        "purpose": "Join table mapping stock instruments to index instruments with weights and effective dates",
        "primary_key": "id",
        "date_column": "effective_date, created_at",
        "symbol_column": "index_instrument_id, stock_instrument_id",
        "universe_role": "UNIVERSE_MEMBERSHIP",
        "authoritative_domain": "Index Composition Master",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Canonical source for Stock-to-Sector and Stock-to-Index mapping",
        "notes": "Relational composition of indices"
    },
    {
        "schema": "public",
        "table_name": "instruments",
        "purpose": "Master instrument table for all stocks, indices, ETFs, and benchmarks",
        "primary_key": "id",
        "date_column": "created_at, updated_at",
        "symbol_column": "symbol, yahoo_symbol",
        "universe_role": "MASTER_UNIVERSE",
        "authoritative_domain": "Instrument & Entity Master",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Foreign Key anchor for research entity resolution (stocks & sectors)",
        "notes": "Authoritative instrument repository with NSE symbol, ISIN, sector, industry"
    },
    {
        "schema": "public",
        "table_name": "report_packs",
        "purpose": "Pre-packaged JSON/binary research pack payloads for daily & weekly reports",
        "primary_key": "report_date",
        "date_column": "report_date, built_at",
        "symbol_column": "NONE",
        "universe_role": "REPORT_PAYLOAD",
        "authoritative_domain": "Report Datapack Storage",
        "used_by_rrg": "NO",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Source payload for research report extraction",
        "notes": "Stores generated report JSON blob packs"
    },
    {
        "schema": "public",
        "table_name": "rrg_benchmarks",
        "purpose": "RRG benchmark index definitions (e.g. NIFTY 50, NIFTY 500, Sector indices)",
        "primary_key": "id",
        "date_column": "created_at",
        "symbol_column": "symbol, source_instrument_id",
        "universe_role": "RRG_BENCHMARKS",
        "authoritative_domain": "RRG Benchmark Infrastructure",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Benchmark reference for Sector & Stock rotation research",
        "notes": "Maps benchmark IDs to source instruments"
    },
    {
        "schema": "public",
        "table_name": "rrg_calculation_runs",
        "purpose": "Audit execution table for RRG engine calculation runs",
        "primary_key": "id",
        "date_column": "run_started_at, run_finished_at, week_end",
        "symbol_column": "NONE",
        "universe_role": "RRG_AUDIT",
        "authoritative_domain": "RRG Execution Governance",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Logs status, counts, warnings for RRG calculation batches"
    },
    {
        "schema": "public",
        "table_name": "rrg_config",
        "purpose": "System configuration key-value parameters for RRG engine v1",
        "primary_key": "key",
        "date_column": "N/A",
        "symbol_column": "NONE",
        "universe_role": "RRG_CONFIG",
        "authoritative_domain": "RRG Engine Parameters",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Stores center points, default windows, smooth factor"
    },
    {
        "schema": "public",
        "table_name": "rrg_constituents",
        "purpose": "Historical constituent memberships and weights for RRG benchmark universes",
        "primary_key": "benchmark_id, instrument_id, effective_date",
        "date_column": "effective_date, created_at",
        "symbol_column": "instrument_id",
        "universe_role": "RRG_CONSTITUENTS",
        "authoritative_domain": "RRG Universe Composition",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "Read-only reference for benchmark membership lookup",
        "notes": "Historical component weights per RRG benchmark"
    },
    {
        "schema": "public",
        "table_name": "rrg_data_quality",
        "purpose": "Data quality audit table flagging missing trading sessions or bad data in RRG inputs",
        "primary_key": "id",
        "date_column": "week_end, created_at",
        "symbol_column": "instrument_id",
        "universe_role": "RRG_QUALITY",
        "authoritative_domain": "RRG Data Quality Audit",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Tracks session counts and missing candles"
    },
    {
        "schema": "public",
        "table_name": "rrg_engine_v2_config",
        "purpose": "Configuration settings for RRG Engine V2 (JDK Smoothing, EMA parameters)",
        "primary_key": "key",
        "date_column": "N/A",
        "symbol_column": "NONE",
        "universe_role": "RRG_CONFIG",
        "authoritative_domain": "RRG V2 Parameters",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "V2 engine configuration settings"
    },
    {
        "schema": "public",
        "table_name": "rrg_events",
        "purpose": "Detected RRG quadrant transition and rotation event log",
        "primary_key": "id",
        "date_column": "week_end, created_at",
        "symbol_column": "instrument_id",
        "universe_role": "RRG_EVENTS",
        "authoritative_domain": "RRG Signals & Transition Events",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Quantitative signal input for research layer event correlation",
        "notes": "Logs quadrant transitions (e.g. Improving -> Leading)"
    },
    {
        "schema": "public",
        "table_name": "rrg_instruments",
        "purpose": "RRG active instrument master mapped to public.instruments",
        "primary_key": "id",
        "date_column": "source_updated_at, created_at",
        "symbol_column": "symbol, yahoo_symbol, source_instrument_id",
        "universe_role": "RRG_INSTRUMENTS",
        "authoritative_domain": "RRG Instrument Master",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only lookup for RRG visualizations",
        "notes": "RRG-specific instrument shadow table linked to main instruments"
    },
    {
        "schema": "public",
        "table_name": "rrg_metrics_v2",
        "purpose": "Authoritative RRG calculated metrics (RS-Ratio, RS-Momentum, Quadrant, Heading, Returns)",
        "primary_key": "instrument_id, benchmark_id, universe_type, week_end, calculation_version",
        "date_column": "week_end, data_date, created_at",
        "symbol_column": "instrument_id",
        "universe_role": "RRG_METRICS",
        "authoritative_domain": "RRG Relative Rotation Analytics",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Core quantitative input for Sector Rotation & Stock Momentum Research",
        "notes": "Contains weekly RS-Ratio, RS-Momentum, quadrant (Leading/Weakening/Lagging/Improving)"
    },
    {
        "schema": "public",
        "table_name": "rrg_universe_v2",
        "purpose": "RRG universe definition table mapping parent benchmarks to instruments",
        "primary_key": "parent_benchmark_id, instrument_id",
        "date_column": "N/A",
        "symbol_column": "instrument_id, benchmark_instrument_id",
        "universe_role": "RRG_UNIVERSE_DEFS",
        "authoritative_domain": "RRG Universe Hierarchy",
        "used_by_rrg": "YES",
        "used_by_eod": "NO",
        "proposed_research_dependency": "Read-only universe lookup",
        "notes": "Defines stock-to-sector and sector-to-index parentage for RRG"
    },
    {
        "schema": "public",
        "table_name": "rrg_week_picker",
        "purpose": "RRG Friday week-end date lookup calendar table",
        "primary_key": "week_end_friday",
        "date_column": "week_end_friday, data_date, created_at",
        "symbol_column": "NONE",
        "universe_role": "CALENDAR",
        "authoritative_domain": "Weekly Calendar Master",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only weekly date boundary alignment",
        "notes": "Ensures standard Friday week-ending alignment for weekly calculations"
    },
    {
        "schema": "public",
        "table_name": "weekly_indicators",
        "purpose": "Weekly technical indicators (e.g. RSI_14 weekly)",
        "primary_key": "instrument_id, week_end",
        "date_column": "week_end",
        "symbol_column": "instrument_id",
        "universe_role": "QUANTITATIVE_INDICATORS",
        "authoritative_domain": "Weekly Technical Indicators",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Read-only input for Weekly Brief research",
        "notes": "Stores weekly timeframe indicators"
    },
    {
        "schema": "public",
        "table_name": "weekly_prices",
        "purpose": "Weekly OHLCV aggregated price series for instruments",
        "primary_key": "instrument_id, week_end",
        "date_column": "week_end",
        "symbol_column": "instrument_id",
        "universe_role": "QUANTITATIVE_PRICES",
        "authoritative_domain": "Weekly Market Prices (OHLCV)",
        "used_by_rrg": "YES",
        "used_by_eod": "YES",
        "proposed_research_dependency": "Weekly price series reference for research analysis",
        "notes": "Aggregated weekly bar price database"
    },
    {
        "schema": "supabase_migrations",
        "table_name": "schema_migrations",
        "purpose": "Supabase migration history tracking table",
        "primary_key": "version",
        "date_column": "N/A",
        "symbol_column": "NONE",
        "universe_role": "SYSTEM",
        "authoritative_domain": "Database Schema Migrations",
        "used_by_rrg": "NO",
        "used_by_eod": "NO",
        "proposed_research_dependency": "NONE",
        "notes": "Supabase internal CLI migration version tracker"
    }
]

def main():
    out_file = "PHASE_3_TABLE_MAP.csv"
    fieldnames = [
        "schema", "table_name", "purpose", "primary_key", "date_column",
        "symbol_column", "universe_role", "authoritative_domain", "used_by_rrg",
        "used_by_eod", "proposed_research_dependency", "notes"
    ]

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in TABLE_MAPPINGS:
            writer.writerow(row)

    print(f"PHASE_3_TABLE_MAP.csv written successfully with {len(TABLE_MAPPINGS)} entries.")

if __name__ == "__main__":
    main()
