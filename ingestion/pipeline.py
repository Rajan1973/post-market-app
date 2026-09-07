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

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    summary = pipeline.run_full_ingestion()
    print("Full Corpus Ingestion Run Completed:")
    print(json.dumps({
        "total_inventory_count": summary["total_inventory_count"],
        "processed_count": summary["processed_count"],
        "unresolved_entities_count": summary["unresolved_entities_count"],
        "sample_results": summary["results"][:4]
    }, indent=2))
