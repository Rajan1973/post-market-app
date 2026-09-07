"""
Non-Destructive Database Connectivity & Schema Verification Script for NIFTY & BEYOND.
This script performs ONLY read-only queries (information_schema inspection).
It does NOT insert, update, delete, or alter any database records or schemas.
Enforces strict project reference verification and protects nifty500data.
"""

import os
import re
import sys
from typing import Dict, List, Any
import dotenv

# Load environment variables from .env
dotenv.load_dotenv()

from config.settings import settings

NIFTY500DATA_PROJECT_REF = "wtbufledttydooazwiuw"

REQUIRED_TABLES = [
    "reports", "report_sections", "sectors", "stocks", "themes",
    "entity_aliases", "report_mentions", "entity_relationships", "unresolved_entities",
    "market_metrics", "stock_metrics", "sector_metrics", "sector_flexible_metrics",
    "sector_rotation", "research_events", "signals", "signal_evidence"
]

def extract_project_ref(db_url: str, supabase_url: str) -> str:
    """Extract project reference safely without exposing passwords or sensitive details."""
    if db_url:
        # Pattern matching postgres.<project_ref> in user field
        match = re.search(r"postgres\.([a-zA-Z0-9_-]+):", db_url)
        if match:
            return match.group(1)
        # Pattern matching host domain <project_ref>.supabase.co or db.<project_ref>.supabase.co
        match_host = re.search(r"@(?:db\.)?([a-zA-Z0-9_-]+)\.supabase\.", db_url)
        if match_host:
            return match_host.group(1)
            
    if supabase_url and "supabase.co" in supabase_url:
        match_sub = re.search(r"https://([a-zA-Z0-9_-]+)\.supabase\.co", supabase_url)
        if match_sub:
            return match_sub.group(1)

    return "UNKNOWN"

def extract_db_host(db_url: str) -> str:
    """Extract host domain safely without credentials."""
    if "@" in db_url:
        host_part = db_url.split("@")[-1]
        host = host_part.split("/")[0].split(":")[0]
        return host
    return "UNKNOWN_HOST"

def check_connectivity() -> Dict[str, Any]:
    """Perform non-destructive connectivity check against target database."""
    print("=== NIFTY & BEYOND Dedicated Research Database Connection Check ===")
    
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    supabase_url = os.getenv("SUPABASE_URL", settings.SUPABASE_URL)
    expected_ref = settings.EXPECTED_PROJECT_REF

    actual_project_ref = extract_project_ref(db_url, supabase_url)
    db_host = extract_db_host(db_url)
    target_is_nifty500data = (actual_project_ref == NIFTY500DATA_PROJECT_REF)
    project_identity_verified = (actual_project_ref == expected_ref and not target_is_nifty500data and actual_project_ref != "UNKNOWN")

    print(f"Database host: {db_host}")
    print(f"Target project reference: {actual_project_ref}")
    print(f"Expected project reference: {expected_ref}")
    print(f"Project identity verified: {'YES' if project_identity_verified else 'NO'}")
    print(f"Target is nifty500data: {'YES (BLOCKED)' if target_is_nifty500data else 'NO'}")
    print(f"Safety Switch (PRODUCTION_INGEST_ENABLED): {settings.PRODUCTION_INGEST_ENABLED}")

    if target_is_nifty500data:
        return {
            "status": "BLOCKED_NIFTY500DATA",
            "db_reachable": True,
            "db_host": db_host,
            "target_project_ref": actual_project_ref,
            "expected_project_ref": expected_ref,
            "project_identity_verified": False,
            "target_is_nifty500data": True,
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "message": f"CRITICAL SAFETY HALT: Configured connection points to nifty500data ({NIFTY500DATA_PROJECT_REF}). Refusing execution."
        }

    if not db_url or "your-supabase-project" in db_url:
        return {
            "status": "NOT_CONFIGURED",
            "db_reachable": False,
            "db_host": db_host,
            "target_project_ref": actual_project_ref,
            "expected_project_ref": expected_ref,
            "project_identity_verified": False,
            "target_is_nifty500data": False,
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "message": "Database credentials are default placeholders. Please configure DATABASE_URL in .env."
        }

    # Test connection via psycopg2
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Read-only metadata query
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        existing_tables = set(row[0] for row in cursor.fetchall())
        
        cursor.close()
        conn.close()

        research_tables_present = [t for t in REQUIRED_TABLES if t in existing_tables]
        missing_tables = [t for t in REQUIRED_TABLES if t not in existing_tables]

        return {
            "status": "CONNECTED",
            "db_reachable": True,
            "db_host": db_host,
            "db_version": db_version,
            "target_project_ref": actual_project_ref,
            "expected_project_ref": expected_ref,
            "project_identity_verified": project_identity_verified,
            "target_is_nifty500data": False,
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "existing_tables_count": len(existing_tables),
            "research_tables_found_count": len(research_tables_present),
            "research_tables_present": research_tables_present,
            "missing_tables": missing_tables
        }
    except Exception as e:
        return {
            "status": "CONNECTION_FAILED",
            "db_reachable": False,
            "db_host": db_host,
            "target_project_ref": actual_project_ref,
            "expected_project_ref": expected_ref,
            "project_identity_verified": False,
            "target_is_nifty500data": False,
            "error": str(e),
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED
        }

if __name__ == "__main__":
    result = check_connectivity()
    print("\nConnection Check Result Summary:")
    # Print redacted summary without exposing sensitive credentials
    safe_result = {k: v for k, v in result.items() if k not in ("error",)}
    if "error" in result:
        safe_result["error_message"] = str(result["error"]).split("\n")[0]
    import json
    print(json.dumps(safe_result, indent=2))
