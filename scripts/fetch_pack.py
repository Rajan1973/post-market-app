"""
fetch_pack.py -- fetch a report_packs row from Supabase and cache it locally.

Usage:
    python scripts/fetch_pack.py 2026-09-04       # fetch specific date
    python scripts/fetch_pack.py                  # fetch latest available

Output: data/packs/<date>.json
"""
import os, sys, json
from datetime import datetime, timezone, timedelta
import psycopg2
import psycopg2.extras

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
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
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env"); sys.exit(1)

IST = timezone(timedelta(hours=5, minutes=30))

def main():
    args = sys.argv[1:]
    date_arg = next((a for a in args if len(a) == 10 and a[4] == "-"), None)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "packs")
    os.makedirs(out_dir, exist_ok=True)

    # Check cache first unless --force
    if date_arg and "--force" not in args:
        cached = os.path.join(out_dir, f"{date_arg}.json")
        if os.path.exists(cached):
            print(f"  Using cached pack: {cached}")
            with open(cached, encoding="utf-8") as f:
                p = json.load(f)
            _print_summary(p, date_arg)
            return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        print(f"ERROR: Connection failed: {e}"); sys.exit(1)

    if date_arg:
        cur.execute(
            "SELECT report_date::text AS d, pack FROM report_packs WHERE report_date = %s::date",
            (date_arg,)
        )
    else:
        cur.execute(
            "SELECT report_date::text AS d, pack FROM report_packs ORDER BY report_date DESC LIMIT 1"
        )

    row = cur.fetchone()
    if not row:
        if date_arg:
            print(f"ERROR: No pack found for {date_arg}.")
            print("       The nightly pipeline may not have run, or the pack step failed silently.")
            print("       Run health_check.py to see what data is present.")
        else:
            print("ERROR: report_packs table is empty. Pipeline has not run yet.")
        cur.close(); conn.close(); sys.exit(1)

    pack_date = row["d"]
    pack = row["pack"]
    cur.close(); conn.close()

    out_path = os.path.join(out_dir, f"{pack_date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print(f"  Pack saved: {out_path}")
    _print_summary(pack, pack_date)

def _print_summary(pack, pack_date):
    q = pack.get("quality", {})
    warnings = q.get("warnings", [])
    print(f"\n  {'='*56}")
    print(f"  Pack: {pack_date}  v{pack.get('pack_version', '?')}  coverage {q.get('coverage_pct', '?')}%")
    print(f"  Built at: {pack.get('built_at', '?')}")
    sections = [k for k in pack if k.startswith("s")]
    print(f"  Sections present: {', '.join(sorted(sections))}")
    not_in = pack.get("not_in_pack", [])
    if not_in:
        print(f"  NOT in pack (supply separately): {', '.join(not_in)}")
    if warnings:
        print(f"\n  DATA WARNINGS ({len(warnings)}) -- disclose in report:")
        for w in warnings:
            print(f"    - {w}")
    else:
        print(f"  No data warnings.")

    # s3 candidate count -- critical for positional §3
    s3 = pack.get("s3_unusual", {})
    candidates = s3.get("candidates", [])
    print(f"\n  s3_unusual candidates: {len(candidates)} -- write EXACTLY this many anomaly entries")
    for i, c in enumerate(candidates):
        print(f"    [{i}] {c.get('subject', '?')} -- {c.get('reading', '?')}")

    print(f"  {'='*56}\n")

if __name__ == "__main__":
    main()
