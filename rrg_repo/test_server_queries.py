import os, sys, urllib.parse, json, psycopg2, psycopg2.extras
sys.path.append("d:/Anti Gravity/post-market-report")
from scripts.health_check import load_env

load_env()
db_url = os.environ.get("DATABASE_URL")

def query_postgrest(table, query_params):
    select_cols = "*"
    where_clauses = []
    order_by = ""
    
    for k, v in query_params.items():
        if k == "select":
            select_cols = v
        elif k == "order":
            parts = v.split(".")
            col = parts[0]
            direction = parts[1].upper() if len(parts) > 0 else "ASC"
            order_by = f"ORDER BY {col} {direction}"
        elif k == "offset" or k == "limit":
            continue
        else:
            if v.startswith("eq."):
                val = v[3:]
                if val.lower() == "true":
                    where_clauses.append(f"{k} = TRUE")
                elif val.lower() == "false":
                    where_clauses.append(f"{k} = FALSE")
                else:
                    where_clauses.append(f"{k} = '{val}'")
            elif v.startswith("in.(") and v.endswith(")"):
                raw_ids = v[4:-1]
                where_clauses.append(f"{k} IN ({raw_ids})")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    sql = f"SELECT {select_cols} FROM {table} {where_sql} {order_by}"
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    
    out = []
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if hasattr(v, 'isoformat'):
                d[k] = v.isoformat()
        out.append(d)
    return out

if __name__ == "__main__":
    inst = query_postgrest("rrg_instruments", {"select": "id,source_instrument_id,symbol,name,instrument_type", "is_active": "eq.true"})
    print("Instruments fetched:", len(inst), "Sample:", inst[0] if inst else None)
    
    bench = query_postgrest("rrg_benchmarks", {"select": "id,symbol,name", "is_active": "eq.true", "order": "name.asc"})
    print("Benchmarks fetched:", len(bench), "Sample:", bench[0] if bench else None)
    
    if bench:
        b_id = bench[0]['id']
        metrics = query_postgrest("rrg_metrics_v2", {
            "select": "instrument_id,benchmark_id,week_end,rs_ratio,rs_momentum,quadrant,direction",
            "benchmark_id": f"eq.{b_id}",
            "universe_type": "eq.INDEX",
            "calculation_version": "eq.v2-ema10-jdk-public",
            "order": "week_end.asc"
        })
        print("Metrics fetched for benchmark", b_id, ":", len(metrics), "Sample:", metrics[0] if metrics else None)
