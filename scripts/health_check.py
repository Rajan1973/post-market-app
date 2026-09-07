"""
health_check.py — quick read from Supabase to confirm data is current.

Usage:
    python scripts/health_check.py

Reads from: daily_prices, index_breadth, fii_dii_cash_market_daily,
            report_packs, weekly_indicators, rrg_metrics_v2
"""
import os, sys
from datetime import date, datetime, timezone, timedelta
import psycopg2

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k and k not in os.environ:
                        os.environ[k] = v

load_env()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Add it to d:\\Anti Gravity\\post-market-report\\.env")
    sys.exit(1)

QUERIES = [
    ("daily_prices",              "SELECT max(date)::text FROM daily_prices"),
    ("daily_indicators",          "SELECT max(date)::text FROM daily_indicators"),
    ("index_breadth",             "SELECT max(date)::text FROM index_breadth"),
    ("fii_dii_cash_market_daily", "SELECT max(date)::text FROM fii_dii_cash_market_daily"),
    ("report_packs",              "SELECT max(report_date)::text FROM report_packs"),
    ("weekly_indicators",         "SELECT max(week_end)::text FROM weekly_indicators"),
    ("rrg_metrics_v2",            "SELECT max(week_end)::text FROM rrg_metrics_v2"),
]

PACK_LIST_QUERY = """
    SELECT report_date::text, pack_version, pg_column_size(pack) AS bytes
    FROM report_packs ORDER BY report_date DESC
"""

IST = timezone(timedelta(hours=5, minutes=30))
today_ist = datetime.now(IST).date()

def main():
    print(f"\n{'='*60}")
    print(f"  NIFTY & BEYOND -- Supabase health check")
    print(f"  Run at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"{'='*60}\n")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        print(f"  X Connection failed: {e}")
        print("\n  Tip: if you see password authentication failed, try percent-encoding")
        print("  the @ in the password to %40 in DATABASE_URL.\n")
        sys.exit(1)
    print(f"  OK Connected to Supabase (nifty500data)\n")
    print(f"  {'Table':<32} {'Latest date':<14} {'Status'}")
    print(f"  {'-'*32} {'-'*14} {'-'*20}")
    all_ok = True
    for table, query in QUERIES:
        try:
            cur.execute(query)
            row = cur.fetchone()
            latest = row[0] if row else None
            if latest is None:
                status = "WARN no data"; all_ok = False
            else:
                latest_date = date.fromisoformat(latest)
                delta = (today_ist - latest_date).days
                if delta == 0:   status = "OK today"
                elif delta == 1: status = "OK yesterday (normal if pre-close)"
                elif delta <= 3: status = f"WARN {delta}d ago -- check pipeline"; all_ok = False
                else:            status = f"FAIL {delta}d ago -- pipeline may be down"; all_ok = False
            print(f"  {table:<32} {latest or '--':<14} {status}")
        except Exception as e:
            print(f"  {table:<32} {'ERROR':<14} FAIL {e}"); all_ok = False
    print()
    try:
        cur.execute(PACK_LIST_QUERY)
        rows = cur.fetchall()
        if rows:
            print(f"  report_packs contents ({len(rows)} rows):")
            for r in rows:
                kb = round(r[2] / 1024, 1) if r[2] else "?"
                print(f"    {r[0]}  v{r[1]}  {kb} KB")
        else:
            print("  report_packs: empty"); all_ok = False
    except Exception as e:
        print(f"  report_packs list failed: {e}")
    cur.close(); conn.close()
    print()
    if all_ok: print(f"  OK All checks passed. Ready to generate a report.\n")
    else:       print(f"  WARN Some checks failed. Resolve before generating.\n")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
