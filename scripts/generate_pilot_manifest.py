"""
generate_pilot_manifest.py
Generates the Phase 2B 7-Report Pilot Manifest with SHA-256 digests and file metadata.
"""

import hashlib
import json
import os
from pathlib import Path
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parsers.eod import EODReportParser
from parsers.sector import SectorReportParser

PILOT_FILES = [
    ("EOD Daily", Path(r"D:\Anti Gravity\post-market-report\reports\rendered\2026-09-04-daily-brief.html"), "2026-09-04", "EOD"),
    ("EOD Daily", Path(r"D:\Anti Gravity\post-market-report\reports\rendered\2026-09-03-daily-brief.html"), "2026-09-03", "EOD"),
    ("EOD Daily", Path(r"D:\Anti Gravity\post-market-report\reports\rendered\2026-09-01-daily-brief.html"), "2026-09-01", "EOD"),
    ("EOD Weekly", Path(r"D:\Anti Gravity\post-market-report\reports\rendered\2026-09-04-weekly-brief.html"), "2026-09-04", "EOD"),
    ("Sector Research", Path(r"D:\Anti Gravity\stock-reports-with-Antigravity\outputs\metals-mining-q1fy27-sector-review.html"), "2026-09-04", "SECTOR_RESEARCH"),
    ("Sector Research", Path(r"D:\Anti Gravity\stock-reports-with-Antigravity\outputs\gold-jewellery-q1fy27-sector-review.html"), "2026-09-04", "SECTOR_RESEARCH"),
    ("Sector Research", Path(r"D:\Anti Gravity\stock-reports-with-Antigravity\outputs\power-generation-q1fy27-sector-review.html"), "2026-09-04", "SECTOR_RESEARCH")
]

def main():
    manifest_reports = []
    print(f"{'Report Type':<15} | {'File':<45} | {'SHA-256':<64} | {'Size (bytes)':>12} | {'Report Date':<11}")
    print("-" * 155)

    for rtype, fpath, rdate, ptype in PILOT_FILES:
        if not fpath.exists():
            print(f"ERROR: File not found: {fpath}")
            sys.exit(1)

        content = fpath.read_bytes()
        sha256 = hashlib.sha256(content).hexdigest()
        size = len(content)

        if ptype == "EOD":
            parser = EODReportParser(fpath, sha256)
        else:
            parser = SectorReportParser(fpath, sha256)

        parsed = parser.parse().to_dict()
        stocks = [s.get("symbol") for s in parsed["entities"]["stocks"]]
        sectors = [s.get("name") for s in parsed["entities"]["sectors"]]

        print(f"{rtype:<15} | {fpath.name:<45} | {sha256} | {size:>12} | {rdate:<11}")

        manifest_reports.append({
            "filename": fpath.name,
            "absolute_path": str(fpath),
            "sha256": sha256,
            "size_bytes": size,
            "report_type": rtype,
            "report_date": rdate,
            "parser_class": parser.__class__.__name__,
            "expected_stocks_count": len(stocks),
            "expected_sectors_count": len(sectors),
            "sample_stocks": stocks[:5],
            "sample_sectors": sectors[:5]
        })

    out_dir = Path("reports/pilot")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "PHASE_2B_PILOT_MANIFEST.json"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "pilot_name": "Phase 2B 7-Report Pilot Manifest",
            "total_reports": len(manifest_reports),
            "reports": manifest_reports
        }, f, indent=2)

    print(f"\nManifest successfully written to {manifest_path}")

if __name__ == "__main__":
    main()
