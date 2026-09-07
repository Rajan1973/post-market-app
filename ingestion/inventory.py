import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file without modifying or locking it."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def classify_report(file_path: Path) -> Dict[str, Any]:
    """Classify report type, report date, and sector based on path and file contents."""
    filename = file_path.name.lower()
    report_type = "UNKNOWN"
    report_date: Optional[str] = None
    sector: Optional[str] = None

    # Check filename patterns for EOD
    if "daily-brief" in filename or "weekly-brief" in filename or "weekly-report" in filename:
        report_type = "EOD"
        # Extract YYYY-MM-DD from filename if present
        parts = filename.split("-")
        if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) == 4:
            report_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
    elif "sector-review" in filename or "example-cement" in filename:
        report_type = "SECTOR_RESEARCH"
        # Extract probable sector name
        raw_sector = filename.replace("-sector-review.html", "").replace(".html", "")
        sector = raw_sector.replace("-q1fy27", "").replace("-", " ").title()

    # Content-based verification if type is still UNKNOWN
    if report_type == "UNKNOWN" and file_path.suffix in [".html", ".htm"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(4096)
                if "NIFTY & BEYOND" in content or "Nifty &amp; Beyond" in content:
                    report_type = "EOD"
                elif "SECTOR EARNINGS REVIEW" in content or "SECTOR REVIEW" in content:
                    report_type = "SECTOR_RESEARCH"
        except Exception:
            pass

    return {
        "report_type": report_type,
        "report_date": report_date,
        "sector": sector
    }

def generate_inventory(source_dirs: List[Path]) -> List[Dict[str, Any]]:
    """Scan directories recursively and build inventory records."""
    inventory = []
    supported_extensions = {".html", ".htm", ".pdf"}

    for sdir in source_dirs:
        if not sdir.exists():
            continue
        for root, _, files in os.walk(sdir):
            for file in files:
                fpath = Path(root) / file
                if fpath.suffix.lower() not in supported_extensions:
                    continue

                stat = fpath.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
                sha256 = compute_sha256(fpath)
                classification = classify_report(fpath)

                inventory.append({
                    "source_directory": str(sdir),
                    "file_path": str(fpath),
                    "filename": fpath.name,
                    "extension": fpath.suffix.lower(),
                    "file_size": stat.st_size,
                    "modified_date": mod_time,
                    "sha256": sha256,
                    "probable_report_type": classification["report_type"],
                    "probable_report_date": classification["report_date"],
                    "probable_sector": classification["sector"]
                })

    return inventory

if __name__ == "__main__":
    import json
    from config.settings import settings
    inv = generate_inventory([settings.EOD_REPORT_PATH, settings.SECTOR_REPORT_PATH])
    print(f"Discovered {len(inv)} report files across source directories.")
    print(json.dumps(inv[:3], indent=2))
