import unittest
from pathlib import Path
from config.settings import settings
from ingestion.inventory import generate_inventory, compute_sha256

class TestInventory(unittest.TestCase):

    def test_inventory_discovery(self):
        inv = generate_inventory([settings.EOD_REPORT_PATH, settings.SECTOR_REPORT_PATH])
        self.assertGreater(len(inv), 0, "Inventory should discover report files")
        
        # Check mandatory record keys
        required_keys = {
            "source_directory", "file_path", "filename", "extension",
            "file_size", "modified_date", "sha256", "probable_report_type",
            "probable_report_date", "probable_sector"
        }
        for rec in inv:
            self.assertTrue(required_keys.issubset(rec.keys()), f"Missing keys in record {rec['filename']}")
            self.assertEqual(len(rec["sha256"]), 64, "SHA-256 hash must be 64 chars hex")

    def test_sha256_reproducibility(self):
        sample_file = settings.EOD_REPORT_PATH / "2026-09-04-daily-brief.html"
        if sample_file.exists():
            h1 = compute_sha256(sample_file)
            h2 = compute_sha256(sample_file)
            self.assertEqual(h1, h2, "SHA-256 hash computation must be deterministic and reproducible")

if __name__ == "__main__":
    unittest.main()
