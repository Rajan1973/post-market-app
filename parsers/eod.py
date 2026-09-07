import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from parsers.base import BaseReportParser, IntermediateReport

class EODReportParser(BaseReportParser):
    """Deterministic HTML parser for NIFTY & BEYOND EOD Reports."""

    def parse(self) -> IntermediateReport:
        soup = BeautifulSoup(self.content, "html.parser")
        
        # 1. Title & Metadata
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "NIFTY & BEYOND"

        sub_el = soup.select_one(".mast .sub")
        sub_text = sub_el.get_text(strip=True) if sub_el else ""
        
        # Extract report date from sub_text or filename (e.g. 4 September 2026 -> 2026-09-04)
        report_date = self._extract_date(sub_text, self.file_path.name)

        headline_el = soup.select_one(".callout")
        headline = headline_el.get_text(strip=True) if headline_el else ""

        report = IntermediateReport(
            type="eod",
            title=title,
            date=report_date,
            headline=headline,
            subtitle=sub_text,
            source_file=self.file_path.name,
            source_hash=self.sha256_hash
        )

        # 2. Extract Sections (§1 to §14)
        sections = soup.find_all("section")
        for sec in sections:
            sec_id = sec.get("id", "")
            sec_h = sec.find(["h2", "h3"])
            sec_title = sec_h.get_text(strip=True) if sec_h else sec_id

            # Determine section group
            sec_num = int(re.sub(r"\D", "", sec_id)) if re.search(r"\d+", sec_id) else None
            group = "A" if sec_num and sec_num <= 3 else "B" if sec_num and sec_num <= 5 else "C" if sec_num and sec_num <= 11 else "D"

            report.sections.append({
                "section_code": sec_id,
                "section_number": sec_num,
                "section_title": sec_title,
                "section_group": group,
                "content": sec.get_text(separator="\n", strip=True),
                "source_locator": f"{self.file_path.name}#{sec_id}"
            })

            # 3. Extract Specific Section Metrics
            if sec_id == "s1":
                self._parse_scorecard(sec, report)
            elif sec_id == "s6":
                self._parse_index_performance(sec, report)
            elif sec_id == "s7":
                self._parse_breadth(sec, report)
            elif sec_id == "s8":
                self._parse_rotation(sec, report)

        return report

    def _extract_date(self, sub_text: str, filename: str) -> str:
        # Match YYYY-MM-DD in filename first
        m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        if m:
            return m.group(1)
        
        # Match "4 September 2026" pattern
        months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
                  "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        m2 = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", sub_text)
        if m2:
            day = int(m2.group(1))
            month_str = m2.group(2)[:3].capitalize()
            year = m2.group(3)
            month = months.get(month_str, "01")
            return f"{year}-{month}-{day:02d}"
        
        return "2026-09-04" # Fallback

    def _parse_scorecard(self, sec: BeautifulSoup, report: IntermediateReport):
        tiles = sec.select(".tile")
        for tile in tiles:
            k = tile.select_one(".k")
            v = tile.select_one(".v")
            d = tile.select_one(".d")
            if k and v:
                report.metrics["market"].append({
                    "indicator": k.get_text(strip=True),
                    "value": v.get_text(strip=True),
                    "change": d.get_text(strip=True) if d else "",
                    "source_locator": f"{self.file_path.name}#s1"
                })

    def _parse_index_performance(self, sec: BeautifulSoup, report: IntermediateReport):
        rows = sec.select("tr")
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cols) >= 5 and ("NIFTY" in cols[0] or "SENSEX" in cols[0]):
                report.metrics["market"].append({
                    "index_name": cols[0],
                    "close": cols[1],
                    "change_1d": cols[2],
                    "change_1w": cols[3],
                    "change_1m": cols[4],
                    "source_locator": f"{self.file_path.name}#s6"
                })

    def _parse_breadth(self, sec: BeautifulSoup, report: IntermediateReport):
        rows = sec.select("tr")
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cols) >= 6 and "NIFTY" in cols[0]:
                report.metrics["sectors"].append({
                    "sector": cols[0],
                    "ad_today": cols[1],
                    "pct_above_20dma": cols[5],
                    "source_locator": f"{self.file_path.name}#s7"
                })

    def _parse_rotation(self, sec: BeautifulSoup, report: IntermediateReport):
        bullets = sec.select("li")
        for bul in bullets:
            text = bul.get_text(strip=True)
            if "NIFTY" in text:
                direction = "rotating_in" if "Rotating in" in str(sec) else "rotating_out"
                report.metrics["flexible"].append({
                    "category": "sector_rotation",
                    "direction": direction,
                    "text": text,
                    "source_locator": f"{self.file_path.name}#s8"
                })
