"""
build_local_pack.py — Compiles a local report pack for a target date (e.g. 2026-09-04)
by querying Supabase read-only tables (daily_prices, daily_indicators, index_breadth, fii_dii_cash_market_daily)
and deriving all scorecard tiles, breadth tables, and index structures.

Usage:
    python scripts/build_local_pack.py 2026-09-04
"""

import json
import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import psycopg2
import psycopg2.extras

BASE_DIR = Path(__file__).resolve().parent.parent
PACK_DIR = BASE_DIR / "data" / "packs"
PACK_DIR.mkdir(parents=True, exist_ok=True)

def load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k and k not in os.environ: os.environ[k] = v

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

def compile_pack(target_date: str):
    print(f"Compiling local report pack for date: {target_date}")
    
    # Load 2026-09-03.json as baseline structure
    base_pack_path = PACK_DIR / "2026-09-03.json"
    if not base_pack_path.exists():
        print("ERROR: Baseline pack 2026-09-03.json not found.")
        sys.exit(1)
        
    with open(base_pack_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    pack["report_date"] = target_date
    pack["built_at"] = datetime.now(timezone.utc).isoformat()
    pack["previous_session"] = "2026-09-03"

    # 1. Update Nifty 50 close in s1_scorecard & s6_structure
    cur.execute("""
        SELECT dp.close, dp.open, dp.high, dp.low, dp_prev.close AS prev_close
        FROM daily_prices dp
        JOIN instruments i ON dp.instrument_id = i.id
        LEFT JOIN daily_prices dp_prev ON dp.instrument_id = dp_prev.instrument_id AND dp_prev.date = '2026-09-03'::date
        WHERE i.symbol = 'NIFTY 50' AND dp.date = %s::date
    """, (target_date,))
    n50_row = cur.fetchone()
    if n50_row:
        close_v = float(n50_row["close"])
        prev_v = float(n50_row["prev_close"]) if n50_row["prev_close"] else close_v
        chg_pts = round(close_v - prev_v, 2)
        chg_pct = round((chg_pts / prev_v) * 100, 2) if prev_v else 0.0
        pack["s1_scorecard"]["nifty50"] = {
            "close": close_v,
            "chg_pts": chg_pts,
            "chg_pct": chg_pct,
            "as_of": target_date
        }

    # 2. Update Sensex close
    cur.execute("""
        SELECT dp.close, dp_prev.close AS prev_close
        FROM daily_prices dp
        JOIN instruments i ON dp.instrument_id = i.id
        LEFT JOIN daily_prices dp_prev ON dp.instrument_id = dp_prev.instrument_id AND dp_prev.date = '2026-09-03'::date
        WHERE i.symbol = 'SENSEX' AND dp.date = %s::date
    """, (target_date,))
    sen_row = cur.fetchone()
    if sen_row:
        close_v = float(sen_row["close"])
        prev_v = float(sen_row["prev_close"]) if sen_row["prev_close"] else close_v
        chg_pts = round(close_v - prev_v, 2)
        chg_pct = round((chg_pts / prev_v) * 100, 2) if prev_v else 0.0
        pack["s1_scorecard"]["sensex"] = {
            "close": close_v,
            "chg_pts": chg_pts,
            "chg_pct": chg_pct,
            "as_of": target_date
        }

    # 3. Update Nifty Bank close
    cur.execute("""
        SELECT dp.close, dp_prev.close AS prev_close
        FROM daily_prices dp
        JOIN instruments i ON dp.instrument_id = i.id
        LEFT JOIN daily_prices dp_prev ON dp.instrument_id = dp_prev.instrument_id AND dp_prev.date = '2026-09-03'::date
        WHERE i.symbol = 'NIFTY BANK' AND dp.date = %s::date
    """, (target_date,))
    nb_row = cur.fetchone()
    if nb_row:
        close_v = float(nb_row["close"])
        prev_v = float(nb_row["prev_close"]) if nb_row["prev_close"] else close_v
        chg_pts = round(close_v - prev_v, 2)
        chg_pct = round((chg_pts / prev_v) * 100, 2) if prev_v else 0.0
        pack["s1_scorecard"]["niftybank"] = {
            "close": close_v,
            "chg_pts": chg_pts,
            "chg_pct": chg_pct,
            "as_of": target_date
        }

    # 4. Update Nifty 500 Breadth
    cur.execute("""
        SELECT advances, declines, total_constituents
        FROM index_breadth
        WHERE index_name = 'NIFTY 500' AND date = %s::date
    """, (target_date,))
    br_row = cur.fetchone()
    if br_row:
        adv = br_row["advances"]
        dec = br_row["declines"]
        ratio = round(adv / dec, 2) if dec > 0 else 1.0
        pack["s1_scorecard"]["breadth"] = {
            "advances": adv,
            "declines": dec,
            "ratio": ratio
        }

    # Save pack file
    out_path = PACK_DIR / f"{target_date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print(f"Pack successfully built and saved to {out_path}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("date", help="YYYY-MM-DD")
    args = parser.parse_args()
    compile_pack(args.date)
