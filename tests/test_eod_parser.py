import unittest
from pathlib import Path
from config.settings import settings
from parsers.eod import EODReportParser

class TestEODParser(unittest.TestCase):

    def test_eod_parsing(self):
        sample_file = settings.EOD_REPORT_PATH / "2026-09-04-daily-brief.html"
        if not sample_file.exists():
            self.skipTest("Sample EOD report file not found")

        parser = EODReportParser(sample_file, "mock_hash_123")
        report = parser.parse()

        self.assertEqual(report.type, "eod")
        self.assertEqual(report.date, "2026-09-04")
        self.assertGreater(len(report.sections), 10, "EOD report should have at least 10 sections")
        self.assertGreater(len(report.metrics["market"]), 0, "Scorecard market metrics should be extracted")

if __name__ == "__main__":
    unittest.main()
