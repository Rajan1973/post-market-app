"""
tijori_client.py — Python bridge to the Tijori Finance MCP server.

Spawns the Node.js MCP as a subprocess and communicates via JSON-RPC 2.0
over stdin/stdout. Designed to be imported by other scripts.

Usage:
    from tijori_client import TijoriClient
    c = TijoriClient()
    result = c.call("search_company", {"query": "BRIGADE"})
    result = c.call("get_macro_indicators", {"tab": "demand"})

Standalone test:
    python scripts/tijori_client.py
"""

import json
import subprocess
import sys
import os
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

TIJORI_DIR = Path(r"D:\Anti Gravity\test-tijori-mcp\tijori-finance-mcp")
TIJORI_ENTRY = TIJORI_DIR / "src" / "index.js"


class TijoriClient:
    """
    Persistent JSON-RPC 2.0 client for the Tijori Finance MCP server.
    Call .close() when done, or use as a context manager.
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._proc = None
        self._req_id = 0
        self._initialized = False

    def _start(self):
        if self._proc and self._proc.poll() is None:
            return  # already running
        env = dict(os.environ)
        # Load .env from Tijori dir
        env_path = TIJORI_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"')
        self._proc = subprocess.Popen(
            ["node", str(TIJORI_ENTRY)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(TIJORI_DIR),
        )

    def _send(self, method: str, params: dict) -> dict:
        self._req_id += 1
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
            "params": params,
        }) + "\n"
        self._proc.stdin.write(req.encode())
        self._proc.stdin.flush()

        # Read until we get a complete JSON line with matching id
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                # EOF — process died
                err = self._proc.stderr.read().decode(errors="replace")
                raise RuntimeError(f"Tijori MCP process died. stderr: {err[:500]}")
            try:
                resp = json.loads(line.decode())
            except json.JSONDecodeError:
                continue  # skip partial / log lines
            if resp.get("id") == self._req_id:
                return resp
        raise TimeoutError(f"Tijori MCP did not respond within {self.timeout}s for method={method}")

    def _initialize(self):
        if self._initialized:
            return
        self._start()
        resp = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "post-market-report", "version": "1.0"},
        })
        if "error" in resp:
            raise RuntimeError(f"Tijori MCP initialize failed: {resp['error']}")
        # Send initialized notification
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        self._proc.stdin.write(notif.encode())
        self._proc.stdin.flush()
        self._initialized = True

    def call(self, tool_name: str, arguments: dict) -> dict:
        """
        Call a Tijori MCP tool. Returns the parsed result dict.
        On error, raises RuntimeError with the error message.
        """
        self._initialize()
        resp = self._send("tools/call", {"name": tool_name, "arguments": arguments})
        if "error" in resp:
            raise RuntimeError(f"Tijori tool '{tool_name}' error: {resp['error']}")
        content = resp.get("result", {}).get("content", [])
        if not content:
            return {}
        text = content[0].get("text", "{}")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
        if isinstance(parsed, dict) and "error" in parsed:
            raise RuntimeError(f"Tijori tool '{tool_name}' returned error: {parsed}")
        return parsed

    def search_company(self, query: str) -> list:
        return self.call("search_company", {"query": query})

    def get_overview(self, slug: str) -> dict:
        return self.call("get_company_overview", {"slug": slug})

    def get_operational_metrics(self, slug: str) -> dict:
        return self.call("get_operational_metrics", {"slug": slug})

    def get_knowledge_base(self, slug: str) -> dict:
        return self.call("get_knowledge_base", {"slug": slug})

    def get_macro_indicators(self, tab: str) -> dict:
        """tab: 'industry' | 'demand' | 'gdp'"""
        return self.call("get_macro_indicators", {"tab": tab})

    def get_raw_materials(self, tab: str) -> dict:
        """tab: 'chemicals' | 'spreads' | 'metals'"""
        return self.call("get_raw_materials", {"tab": tab})

    def get_markets(self, tab: str) -> dict:
        """tab: 'headline' | 'niche' | 'conglomerates'"""
        return self.call("get_markets", {"tab": tab})

    def get_financials(self, slug: str, type_: str) -> dict:
        """type_: 'pl' | 'bs' | 'cf' | 'ratios' | 'quarterly'"""
        return self.call("get_financials", {"slug": slug, "type": type_})

    def resolve_slug(self, name: str) -> str | None:
        """
        Best-effort: search for a company name and return the first slug.
        Returns None if not found.
        """
        try:
            results = self.search_company(name)
            if isinstance(results, list) and results:
                return results[0].get("slug")
        except Exception as e:
            log.warning("resolve_slug(%s): %s", name, e)
        return None

    def close(self):
        if self._proc and self._proc.poll() is None:
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Starting Tijori MCP bridge test...\n")

    tests = [
        ("search_company", {"query": "Brigade"}),
        ("get_macro_indicators", {"tab": "demand"}),
        ("get_raw_materials", {"tab": "metals"}),
        ("get_markets", {"tab": "headline"}),
    ]

    with TijoriClient(timeout=90) as client:
        for tool, args in tests:
            print(f"--- {tool}({args}) ---")
            try:
                result = client.call(tool, args)
                # Print a compact preview
                text = json.dumps(result, indent=2)
                print(text[:800] + ("..." if len(text) > 800 else ""))
            except Exception as e:
                print(f"ERROR: {e}")
            print()

    print("Done.")
