import unittest
from pathlib import Path
from config.settings import settings
from parsers.eod import EODReportParser

class TestMarketMetricsSeparation(unittest.TestCase):

    def test_market_versus_stock_metrics_separation(self):
        sample_file = settings.EOD_REPORT_PATH / "2026-09-04-daily-brief.html"
        if not sample_file.exists():
            self.skipTest("Sample EOD file not found")

        parser = EODReportParser(sample_file, "mock_hash_market_test")
        report = parser.parse()

        # Market metrics must contain Nifty 50, Sensex, VIX, FII/DII cash
        market_indicators = [m["indicator"] for m in report.metrics["market"] if "indicator" in m]
        self.assertTrue(any("Nifty 50" in ind for ind in market_indicators), "Nifty 50 close must be in market metrics")
        self.assertTrue(any("FII" in ind for ind in market_indicators), "FII cash flow must be in market metrics")
        self.assertTrue(any("DII" in ind for ind in market_indicators), "DII cash flow must be in market metrics")

if __name__ == "__main__":
    unittest.main()
