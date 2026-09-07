import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Settings:
    # Source Directory Paths (Read-only)
    EOD_REPORT_PATH: Path = Path(os.getenv("EOD_REPORT_PATH", r"D:\Anti Gravity\post-market-report\reports\rendered"))
    SECTOR_REPORT_PATH: Path = Path(os.getenv("SECTOR_REPORT_PATH", r"D:\Anti Gravity\stock-reports-with-Antigravity\outputs"))
    
    # Production Safety Switch (Must be explicitly set to True in environment to write to production DB)
    PRODUCTION_INGEST_ENABLED: bool = os.getenv("PRODUCTION_INGEST_ENABLED", "false").lower() in ("true", "1", "yes")

    # Expected Target Project Identifier (To prevent writing to the wrong Supabase project)
    EXPECTED_PROJECT_REF: str = os.getenv("EXPECTED_PROJECT_REF", "post-market-app")

    # Supabase / PostgreSQL Credentials
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-supabase-project.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "your-anon-key")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")

settings = Settings()
