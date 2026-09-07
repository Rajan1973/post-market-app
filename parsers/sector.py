import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from parsers.base import BaseReportParser, IntermediateReport

class SectorReportParser(BaseReportParser):
    """Deterministic HTML parser for Sector Research Reports."""

    def parse(self) -> IntermediateReport:
        soup = BeautifulSoup(self.content, "html.parser")

        # 1. Metadata & Header
        eyebrow_el = soup.select_one(".eyebrow")
        eyebrow = eyebrow_el.get_text(strip=True) if eyebrow_el else ""

        h1_el = soup.find("h1")
        h1_text = h1_el.get_text(strip=True) if h1_el else "SECTOR REVIEW"
        
        # Sector name clean
        sector_name = re.sub(r"^\d+\s*/\s*", "", h1_text).strip()

        # Extract publication period (e.g. Q1 FY27)
        period = "Q1 FY27"
        if "Q1 FY27" in eyebrow:
            period = "Q1 FY27"

        report = IntermediateReport(
            type="sector",
            title=f"{sector_name} Sector Review",
            date="2026-09-04",
            subtitle=eyebrow,
            source_file=self.file_path.name,
            source_hash=self.sha256_hash
        )

        report.entities["sectors"].append({
            "name": sector_name,
            "period": period,
            "source_locator": f"{self.file_path.name}#head"
        })

        # 2. Thesis & Synthesis
        synth_el = soup.select_one(".synth")
        if synth_el:
            thesis_text = synth_el.get_text(separator="\n", strip=True)
            report.sections.append({
                "section_code": "thesis",
                "section_title": "Sector Synthesis & Thesis",
                "content": thesis_text,
                "source_locator": f"{self.file_path.name}#.synth"
            })

        # 3. Company Cards Extraction
        cards = soup.select(".grid .c")
        for card in cards:
            logo_mono = card.select_one(".logo .mono")
            co_name = logo_mono.get_text(strip=True) if logo_mono else ""
            badge = card.select_one(".badge")
            badge_text = badge.get_text(strip=True) if badge else ""

            # Extract metrics tiles in company card
            tiles_data = {}
            tiles = card.select(".tile")
            for t in tiles:
                n = t.select_one(".n")
                l = t.select_one(".l")
                if n and l:
                    tiles_data[l.get_text(strip=True)] = n.get_text(strip=True)

            bullets = [li.get_text(strip=True) for li in card.select("li")]
            flags = [f.get_text(strip=True) for f in card.select(".flag")]

            if co_name:
                report.entities["stocks"].append({
                    "symbol": co_name,
                    "company_name": co_name,
                    "guidance_delivery": badge_text,
                    "metrics": tiles_data,
                    "bullets": bullets,
                    "flags": flags,
                    "source_locator": f"{self.file_path.name}#.c"
                })

        # 4. Scissor Analysis Extraction
        scissor = soup.select_one(".scissor")
        if scissor:
            rows = scissor.select(".row")
            for r in rows:
                co = r.select_one(".co")
                if co:
                    report.metrics["flexible"].append({
                        "category": "scissor_analysis",
                        "entity": co.get_text(strip=True),
                        "source_locator": f"{self.file_path.name}#.scissor"
                    })

        # 5. Valuation Calls
        calls = soup.select(".calls .call")
        for call in calls:
            ctype = call.select_one(".type")
            ch3 = call.find("h3")
            ctarget = call.select_one(".target")
            cp = call.find("p")

            if ch3:
                report.metrics["flexible"].append({
                    "category": "valuation_call",
                    "rating": ctype.get_text(strip=True) if ctype else "",
                    "stock": ch3.get_text(strip=True),
                    "target": ctarget.get_text(strip=True) if ctarget else "",
                    "rationale": cp.get_text(strip=True) if cp else "",
                    "source_locator": f"{self.file_path.name}#.call"
                })

        return report
