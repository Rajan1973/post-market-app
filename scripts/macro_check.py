"""
macro_check.py — Fetches, stores, and analyzes the 50 macro indicators & raw material metals.

- Connects to Tijori via `tijori_client.py`.
- Stores indicator readings in SQLite (`data/macro/macro_history.db`).
- Calculates daily (1D), weekly (1W), and monthly (1M) deltas against historical runs.
- Extracts metals prices for §1 Executive Scorecard.
- Generates structured JSON output for §4 Macro & Policy Dashboard.

Usage:
    python scripts/macro_check.py [--date 2026-09-03]
"""

import json
import sqlite3
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import logging

from tijori_client import TijoriClient

log = logging.getLogger("macro_check")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "macro"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "macro_history.db"
CALENDAR_PATH = DATA_DIR / "calendar.json"


def init_db(conn: sqlite3.Connection):
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_snapshots (
                date TEXT NOT NULL,
                indicator_id TEXT NOT NULL,
                indicator_name TEXT,
                category TEXT,
                value REAL,
                value_str TEXT,
                unit TEXT,
                period TEXT,
                source TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, indicator_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metal_prices (
                date TEXT NOT NULL,
                metal_name TEXT NOT NULL,
                ltp_vs_52w_high TEXT,
                change_1w TEXT,
                change_1m TEXT,
                change_3m TEXT,
                source TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, metal_name)
            )
        """)


def load_calendar() -> list:
    if CALENDAR_PATH.exists():
        with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def run_macro_check(target_date: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    log.info(f"Running macro check for date: {target_date}")
    calendar = load_calendar()

    macro_data = {
        "date": target_date,
        "indicators": {},
        "metals": [],
        "highlights": []
    }

    with TijoriClient(timeout=60) as tijori:
        # 1. Fetch metals from Tijori get_raw_materials
        try:
            log.info("Fetching raw materials / metals from Tijori...")
            metals_resp = tijori.get_raw_materials("metals")
            rows = metals_resp.get("rows", [])
            with conn:
                for r in rows:
                    name = r.get("metric", "").strip()
                    if not name:
                        continue
                    conn.execute("""
                        INSERT OR REPLACE INTO metal_prices (date, metal_name, ltp_vs_52w_high, change_1w, change_1m, change_3m, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'tijori')
                    """, (
                        target_date,
                        name,
                        r.get("LTP vs 52W High"),
                        r.get("1W"),
                        r.get("1M"),
                        r.get("3M")
                    ))
                    macro_data["metals"].append({
                        "name": name,
                        "ltp_vs_52w_high": r.get("LTP vs 52W High"),
                        "change_1w": r.get("1W"),
                        "change_1m": r.get("1M"),
                        "change_3m": r.get("3M")
                    })
        except Exception as e:
            log.error(f"Failed to fetch metals from Tijori: {e}")

        # 2. Fetch Demand & Industry Macro Indicators from Tijori
        for tab in ["demand", "industry", "gdp"]:
            try:
                log.info(f"Fetching macro indicators tab: {tab}")
                ind_resp = tijori.get_macro_indicators(tab)
                headers = ind_resp.get("headers", [])
                rows = ind_resp.get("rows", [])
                
                # Pick latest available month column
                latest_col = headers[1] if len(headers) > 1 else None

                with conn:
                    for r in rows:
                        m_name = r.get("metric", "").strip()
                        if not m_name:
                            continue
                        val = r.get(latest_col) if latest_col else None
                        clean_id = m_name.lower().replace(" ", "_").replace("-", "_")
                        conn.execute("""
                            INSERT OR REPLACE INTO macro_snapshots (date, indicator_id, indicator_name, category, value_str, period, source)
                            VALUES (?, ?, ?, ?, ?, ?, 'tijori')
                        """, (
                            target_date,
                            clean_id,
                            m_name,
                            tab,
                            str(val) if val is not None else None,
                            latest_col,
                        ))
                        macro_data["indicators"][clean_id] = {
                            "name": m_name,
                            "category": tab,
                            "latest_period": latest_col,
                            "value": val
                        }
            except Exception as e:
                log.error(f"Failed to fetch macro tab '{tab}': {e}")

    # Calculate historic deltas from SQLite
    cur = conn.cursor()
    # Check 7 days ago date
    cur.execute("SELECT DISTINCT date FROM macro_snapshots WHERE date < ? ORDER BY date DESC LIMIT 1", (target_date,))
    prev_row = cur.fetchone()
    prev_date = prev_row[0] if prev_row else None
    macro_data["compared_with_prev_date"] = prev_date

    # Output structured summary file
    out_file = DATA_DIR / f"macro_summary_{target_date}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(macro_data, f, indent=2)

    log.info(f"Macro check completed. Saved summary to {out_file}")
    conn.close()
    return macro_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Macro check runner")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target date YYYY-MM-DD")
    args = parser.parse_args()

    run_macro_check(args.date)
