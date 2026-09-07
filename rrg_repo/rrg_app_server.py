import os, sys, urllib.parse, json, psycopg2, psycopg2.extras
from decimal import Decimal
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.append("d:/Anti Gravity/post-market-report")
from scripts.health_check import load_env

load_env()
DB_URL = os.environ.get("DATABASE_URL")
REPO_DIR = "d:/Anti Gravity/post-market-report/rrg_repo"
PORT = 8050

def query_postgrest(table, query_params):
    select_cols = "*"
    where_clauses = []
    order_by = ""
    limit_clause = ""
    offset_clause = ""
    
    for k, v in query_params.items():
        if k == "select":
            select_cols = v
            if table == "rrg_week_picker":
                select_cols = select_cols.replace("week_end", "week_end_friday AS week_end")
                select_cols = select_cols.replace("week_number", "EXTRACT(week FROM week_end_friday)::int AS week_number")
        elif k == "order":
            parts = v.split(".")
            col = parts[0]
            if table == "rrg_metrics_v2":
                col = "m." + col
            elif table == "rrg_week_picker" and col == "week_end":
                col = "week_end_friday"
            direction = parts[1].upper() if len(parts) > 1 else "ASC"
            order_by = f"ORDER BY {col} {direction}"
        elif k == "limit":
            limit_clause = f"LIMIT {int(v)}"
        elif k == "offset":
            offset_clause = f"OFFSET {int(v)}"
        else:
            prefix = "m." if table == "rrg_metrics_v2" else ""
            if v.startswith("eq."):
                val = v[3:]
                if val.lower() == "true":
                    where_clauses.append(f"{prefix}{k} = TRUE")
                elif val.lower() == "false":
                    where_clauses.append(f"{prefix}{k} = FALSE")
                else:
                    where_clauses.append(f"{prefix}{k} = '{val}'")
            elif v.startswith("in.(") and v.endswith(")"):
                raw_ids = v[4:-1]
                where_clauses.append(f"{prefix}{k} IN ({raw_ids})")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    if table == "rrg_metrics_v2":
        sql = f"""
            SELECT 
                m.instrument_id, m.benchmark_id, m.universe_type, m.week_end, 
                m.rs_ratio, m.rs_momentum, m.quadrant, m.direction, m.calculation_version,
                d.rsi_14, d.adx_14
            FROM rrg_metrics_v2 m
            LEFT JOIN LATERAL (
                SELECT rsi_14, adx_14 
                FROM daily_indicators 
                WHERE instrument_id = m.instrument_id AND date <= m.week_end 
                ORDER BY date DESC LIMIT 1
            ) d ON TRUE
            {where_sql} {order_by} {limit_clause} {offset_clause}
        """
    else:
        sql = f"SELECT {select_cols} FROM {table} {where_sql} {order_by} {limit_clause} {offset_clause}"

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    
    out = []
    for r in rows:
        d = dict(r)
        for k, val in d.items():
            if isinstance(val, Decimal):
                d[k] = float(val)
            elif hasattr(val, 'isoformat'):
                d[k] = val.isoformat()
        out.append(d)
    return out

class RRGServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = dict(urllib.parse.parse_qsl(parsed.query))
        
        def send_headers(status=200, content_type="text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            
        if path == "/" or path == "/rrg_app_local.html" or path == "/rrg_app_updated.html":
            file_path = os.path.join(REPO_DIR, "rrg_app_local.html")
            if os.path.exists(file_path):
                send_headers(200, "text/html; charset=utf-8")
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                send_headers(404, "text/plain")
                self.wfile.write(b"File not found")
        elif path in ["/rrg-user-manual.html", "/app-vibecoding-guide.md", "/README.md"]:
            file_path = os.path.join(REPO_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                c_type = "text/html" if path.endswith(".html") else "text/plain"
                send_headers(200, c_type)
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                send_headers(404, "text/plain")
                self.wfile.write(b"File not found")
        elif path.startswith("/rest/v1/"):
            table_name = path[len("/rest/v1/"):].strip("/")
            try:
                data = query_postgrest(table_name, query_params)
                send_headers(200, "application/json")
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                send_headers(500, "application/json")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            send_headers(404, "text/plain")
            self.wfile.write(b"Not Found")

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, RRGServerHandler)
    print(f"RRG Local Server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")

if __name__ == "__main__":
    run()
