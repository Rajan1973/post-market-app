import json
from pathlib import Path
from typing import Dict, List, Any
from config.settings import settings
from ingestion.inventory import generate_inventory
from parsers.eod import EODReportParser
from parsers.sector import SectorReportParser
from entity_resolution.resolver import EntityResolver

class IngestionPipeline:
    """Read-only ingestion pipeline orchestrator."""

    def __init__(self):
        self.resolver = EntityResolver()
        self.processed_hashes = set()
        self.logs: List[Dict[str, Any]] = []

    def run_sample_ingestion(self, eod_limit: int = 3, sector_limit: int = 3) -> Dict[str, Any]:
        inventory = generate_inventory([settings.EOD_REPORT_PATH, settings.SECTOR_REPORT_PATH])
        
        # Select sample reports for Phase 1
        eod_samples = [i for i in inventory if i["probable_report_type"] == "EOD"][:eod_limit]
        sector_samples = [i for i in inventory if i["probable_report_type"] == "SECTOR_RESEARCH"][:sector_limit]
        sample_set = eod_samples + sector_samples

        output_dir = Path("reports/normalized_sample")
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for item in sample_set:
            fpath = Path(item["file_path"])
            sha256 = item["sha256"]

            # Duplicate check
            if sha256 in self.processed_hashes:
                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "SKIPPED_DUPLICATE",
                    "hash": sha256
                })
                continue

            self.processed_hashes.add(sha256)

            try:
                if item["probable_report_type"] == "EOD":
                    parser = EODReportParser(fpath, sha256)
                else:
                    parser = SectorReportParser(fpath, sha256)

                parsed_report = parser.parse()
                parsed_dict = parsed_report.to_dict()

                # Entity Resolution Pass
                for stock in parsed_dict["entities"]["stocks"]:
                    res = self.resolver.resolve_entity(stock.get("symbol", ""), "stock", source_report_id=sha256)
                    stock["entity_resolution"] = res

                # Save normalized JSON sample
                out_name = f"{fpath.stem}_normalized.json"
                out_path = output_dir / out_name
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_dict, f, indent=2)

                results.append({
                    "file": item["filename"],
                    "report_type": item["probable_report_type"],
                    "sections_count": len(parsed_dict["sections"]),
                    "entities_count": len(parsed_dict["entities"]["stocks"]) + len(parsed_dict["entities"]["sectors"]),
                    "metrics_count": len(parsed_dict["metrics"]["market"]) + len(parsed_dict["metrics"]["sectors"]) + len(parsed_dict["metrics"]["flexible"]),
                    "normalized_output_path": str(out_path)
                })

                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "SUCCESS",
                    "sections": len(parsed_dict["sections"])
                })

            except Exception as e:
                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "FAILED",
                    "error": str(e)
                })

        return {
            "processed_count": len(results),
            "results": results,
            "unresolved_entities_count": len(self.resolver.unresolved_queue),
            "logs": self.logs
        }

    def run_full_ingestion(self) -> Dict[str, Any]:
        inventory = generate_inventory([settings.EOD_REPORT_PATH, settings.SECTOR_REPORT_PATH])
        output_dir = Path("reports/normalized_full")
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for item in inventory:
            fpath = Path(item["file_path"])
            sha256 = item["sha256"]

            if sha256 in self.processed_hashes:
                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "SKIPPED_DUPLICATE",
                    "hash": sha256
                })
                continue

            self.processed_hashes.add(sha256)

            try:
                if item["probable_report_type"] == "EOD":
                    parser = EODReportParser(fpath, sha256)
                else:
                    parser = SectorReportParser(fpath, sha256)

                parsed_report = parser.parse()
                parsed_dict = parsed_report.to_dict()

                for stock in parsed_dict["entities"]["stocks"]:
                    res = self.resolver.resolve_entity(stock.get("symbol", ""), "stock", source_report_id=sha256)
                    stock["entity_resolution"] = res

                out_name = f"{fpath.stem}_normalized.json"
                out_path = output_dir / out_name
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_dict, f, indent=2)

                results.append({
                    "file": item["filename"],
                    "report_type": item["probable_report_type"],
                    "sections_count": len(parsed_dict["sections"]),
                    "entities_count": len(parsed_dict["entities"]["stocks"]) + len(parsed_dict["entities"]["sectors"]),
                    "metrics_count": len(parsed_dict["metrics"]["market"]) + len(parsed_dict["metrics"]["sectors"]) + len(parsed_dict["metrics"]["flexible"]),
                    "normalized_output_path": str(out_path)
                })

                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "SUCCESS",
                    "sections": len(parsed_dict["sections"])
                })

            except Exception as e:
                self.logs.append({
                    "file": item["filename"],
                    "operation": "PARSE",
                    "status": "FAILED",
                    "error": str(e)
                })

        return {
            "total_inventory_count": len(inventory),
            "processed_count": len(results),
            "results": results,
            "unresolved_entities_count": len(self.resolver.unresolved_queue),
            "unresolved_queue": self.resolver.unresolved_queue,
            "logs": self.logs
        }

    def run_manifest_ingestion(self, manifest_path: str) -> Dict[str, Any]:
        """
        Ingests ONLY reports explicitly listed in the provided manifest file.
        Enforces strict pre-flight validation rules before reading or writing.
        """
        import hashlib
        mpath = Path(manifest_path)
        if not mpath.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(mpath, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        reports = manifest_data.get("reports", [])
        print(f"=== Explicit Manifest Ingestion Mode: {manifest_data.get('pilot_name', 'Custom')} ===")
        print(f"Manifest path: {mpath}")
        print(f"Manifest report count: {len(reports)}")
        print(f"PRODUCTION_INGEST_ENABLED: {settings.PRODUCTION_INGEST_ENABLED}")

        # Pre-flight check 1: Target project reference verification
        if settings.EXPECTED_PROJECT_REF != "post-market-app":
            raise ValueError(f"Safety Violation: EXPECTED_PROJECT_REF '{settings.EXPECTED_PROJECT_REF}' != 'post-market-app'")

        results = []
        for item in reports:
            fpath = Path(item["absolute_path"])
            if not fpath.exists():
                raise FileNotFoundError(f"Source report file missing: {fpath}")

            # Pre-flight check 2: SHA-256 validation
            content = fpath.read_bytes()
            computed_hash = hashlib.sha256(content).hexdigest()
            if computed_hash != item["sha256"]:
                raise ValueError(f"Hash Mismatch for {fpath.name}! Expected: {item['sha256']}, Computed: {computed_hash}")

            # Parse report
            parser_cls_name = item.get("parser_class", "")
            if parser_cls_name == "EODReportParser" or item.get("report_type") in ("EOD Daily", "EOD Weekly"):
                parser = EODReportParser(fpath, computed_hash)
            else:
                parser = SectorReportParser(fpath, computed_hash)

            parsed_dict = parser.parse().to_dict()
            for stock in parsed_dict["entities"]["stocks"]:
                res = self.resolver.resolve_entity(stock.get("symbol", ""), "stock", source_report_id=computed_hash)
                stock["entity_resolution"] = res

            results.append({
                "file": item["filename"],
                "report_type": item["report_type"],
                "sha256": computed_hash,
                "sections_count": len(parsed_dict["sections"]),
                "entities_count": len(parsed_dict["entities"]["stocks"]) + len(parsed_dict["entities"]["sectors"]),
                "parsed_data": parsed_dict
            })

            self.logs.append({
                "file": item["filename"],
                "operation": "MANIFEST_PARSE",
                "status": "VALIDATED_SUCCESS",
                "hash": computed_hash
            })

        return {
            "pilot_manifest": str(mpath),
            "manifest_total": len(reports),
            "processed_count": len(results),
            "production_ingest_enabled": settings.PRODUCTION_INGEST_ENABLED,
            "results": results,
            "logs": self.logs
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NIFTY & BEYOND Ingestion Pipeline")
    parser.add_argument("--manifest", type=str, help="Path to pilot manifest JSON file for explicit pilot ingestion")
    parser.add_argument("--sample", action="store_true", help="Run sample ingestion")
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    if args.manifest:
        summary = pipeline.run_manifest_ingestion(args.manifest)
        print("Manifest Pilot Processing Summary:")
        print(json.dumps({
            "pilot_manifest": summary["pilot_manifest"],
            "processed_count": summary["processed_count"],
            "production_ingest_enabled": summary["production_ingest_enabled"],
            "sample_files": [r["file"] for r in summary["results"]]
        }, indent=2))
    elif args.sample:
        summary = pipeline.run_sample_ingestion()
        print("Sample Ingestion Run Completed:", summary["processed_count"])
    else:
        summary = pipeline.run_full_ingestion()
        print("Full Corpus Ingestion Run Completed:", summary["processed_count"])

