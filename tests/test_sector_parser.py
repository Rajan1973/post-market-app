import unittest
from pathlib import Path
from config.settings import settings
from parsers.sector import SectorReportParser

class TestSectorParser(unittest.TestCase):

    def test_sector_parsing(self):
        sample_file = settings.SECTOR_REPORT_PATH / "metals-mining-q1fy27-sector-review.html"
        if not sample_file.exists():
            self.skipTest("Sample Sector report file not found")

        parser = SectorReportParser(sample_file, "mock_hash_456")
        report = parser.parse()

        self.assertEqual(report.type, "sector")
        self.assertGreater(len(report.entities["sectors"]), 0, "Sector entity should be extracted")
        self.assertGreater(len(report.entities["stocks"]), 0, "Company cards should be extracted")

if __name__ == "__main__":
    unittest.main()
