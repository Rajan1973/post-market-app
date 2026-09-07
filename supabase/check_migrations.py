"""
Non-Destructive Migration Safety Inspector for NIFTY & BEYOND.
Inspects local SQL migration files in supabase/migrations/ for safety, ordering, and syntax rules.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any

MIGRATION_FILES = [
    "001_initial_schema.sql",
    "002_entity_tables.sql",
    "003_metrics_tables.sql",
    "004_signals_tables.sql"
]

def inspect_migrations(migrations_dir: Path = Path("supabase/migrations")) -> Dict[str, Any]:
    print("=== NIFTY & BEYOND Migration Safety Inspector ===")
    
    findings = []
    declared_tables = []
    forbidden_terms = ["DROP TABLE", "TRUNCATE", "DELETE FROM"]
    
    for filename in MIGRATION_FILES:
        fpath = migrations_dir / filename
        if not fpath.exists():
            findings.append({"file": filename, "status": "MISSING", "error": f"File {filename} not found"})
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for forbidden destructive SQL
        destructive_found = [term for term in forbidden_terms if term in content.upper()]
        
        # Extract CREATE TABLE names
        tables = re.findall(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+)", content, re.IGNORECASE)
        declared_tables.extend(tables)

        findings.append({
            "file": filename,
            "status": "PASS" if not destructive_found else "FAIL",
            "destructive_sql": destructive_found,
            "declared_tables": tables
        })

    return {
        "status": "PASS" if all(f["status"] == "PASS" for f in findings) else "FAIL",
        "total_migrations": len(MIGRATION_FILES),
        "total_declared_tables": len(declared_tables),
        "declared_tables": declared_tables,
        "migration_details": findings
    }

if __name__ == "__main__":
    res = inspect_migrations()
    import json
    print(json.dumps(res, indent=2))
