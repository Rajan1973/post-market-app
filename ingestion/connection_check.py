"""
Non-Destructive Database Connectivity & Schema Verification Script for NIFTY & BEYOND.
This script performs ONLY read-only queries (information_schema inspection).
It does NOT insert, update, delete, or alter any database records or schemas.
"""

import sys
from typing import Dict, List, Any
from config.settings import settings

REQUIRED_TABLES = [
    "reports", "report_sections", "sectors", "stocks", "themes",
    "entity_aliases", "report_mentions", "entity_relationships", "unresolved_entities",
    "market_metrics", "stock_metrics", "sector_metrics", "sector_flexible_metrics",
    "sector_rotation", "research_events", "signals", "signal_evidence"
]

def check_connectivity() -> Dict[str, Any]:
    """Perform non-destructive connectivity check against target database."""
    print("=== NIFTY & BEYOND Non-Destructive Connectivity Check ===")
    print(f"Safety Switch (PRODUCTION_INGEST_ENABLED): {settings.PRODUCTION_INGEST_ENABLED}")
    print(f"Target Project Reference: {settings.EXPECTED_PROJECT_REF}")
    
    if not settings.DATABASE_URL and settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        return {
            "status": "NOT_CONFIGURED",
            "message": "Database credentials are currently using default placeholders. Set DATABASE_URL or SUPABASE_* credentials in .env.",
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "checked_tables": []
        }

    # If DATABASE_URL is configured, test psycopg2 / asyncpg connection
    try:
        import psycopg2
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Test basic connectivity
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        
        # 2. Inspect existing tables in public schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        existing_tables = set(row[0] for row in cursor.fetchall())
        
        cursor.close()
        conn.close()

        missing_tables = [t for t in REQUIRED_TABLES if t not in existing_tables]

        return {
            "status": "CONNECTED",
            "db_version": db_version,
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "existing_tables_count": len(existing_tables),
            "required_tables_found": len(REQUIRED_TABLES) - len(missing_tables),
            "missing_tables": missing_tables
        }
    except Exception as e:
        return {
            "status": "CONNECTION_FAILED",
            "error": str(e),
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED
        }

if __name__ == "__main__":
    result = check_connectivity()
    print("\nConnectivity Check Results:")
    print(result)
