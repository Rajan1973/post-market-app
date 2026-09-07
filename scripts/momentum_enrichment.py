"""
momentum_enrichment.py — Enriches Section 10 momentum stocks (Table 1 Fresh + Table 2 Continued)
with deep data from Tijori Finance (overview, operational metrics, knowledge base, recent updates).

- Inputs: report pack JSON (`data/packs/<date>.json`).
- Queries Tijori via `tijori_client.py`.
- Enriches ALL 20 momentum names (both fresh entries and continued momentum).
- Outputs: `data/enrichment/momentum_enriched_<date>.json`.

Usage:
    python scripts/momentum_enrichment.py [--date 2026-09-03]
"""

import json
import sys
import argparse
import logging
from pathlib import Path

from tijori_client import TijoriClient

log = logging.getLogger("momentum_enrichment")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
PACK_DIR = BASE_DIR / "data" / "packs"
ENRICH_DIR = BASE_DIR / "data" / "enrichment"
ENRICH_DIR.mkdir(parents=True, exist_ok=True)


def enrich_momentum_stocks(date_str: str) -> dict:
    pack_path = PACK_DIR / f"{date_str}.json"
    if not pack_path.exists():
        log.error(f"Pack file not found: {pack_path}")
        return {}

    with open(pack_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    s10 = pack.get("s10_momentum", {})
    fresh_list = s10.get("fresh", [])
    cont_list = s10.get("continued", [])

    all_symbols = []
    for item in fresh_list:
        sym = item.get("symbol")
        if sym and sym not in all_symbols:
            all_symbols.append(sym)
    for item in cont_list:
        sym = item.get("symbol")
        if sym and sym not in all_symbols:
            all_symbols.append(sym)

    log.info(f"Found {len(all_symbols)} momentum stocks for enrichment: {all_symbols}")

    enriched_results = {
        "date": date_str,
        "total_stocks": len(all_symbols),
        "stocks": {}
    }

    with TijoriClient(timeout=60) as tijori:
        for sym in all_symbols:
            log.info(f"Enriching stock: {sym} via Tijori...")
            stock_data = {
                "symbol": sym,
                "slug": None,
                "overview": {},
                "operational_metrics": {},
                "knowledge_base": {},
                "recent_quarter": {}
            }

            try:
                slug = tijori.resolve_slug(sym)
                if slug:
                    stock_data["slug"] = slug
                    log.info(f"Resolved {sym} -> slug '{slug}'")

                    # 1. Company Overview
                    try:
                        ov = tijori.get_overview(slug)
                        stock_data["overview"] = ov
                    except Exception as e:
                        log.warning(f"Overview failed for {sym}: {e}")

                    # 2. Operational Metrics
                    try:
                        op = tijori.get_operational_metrics(slug)
                        stock_data["operational_metrics"] = op
                    except Exception as e:
                        log.warning(f"Operational metrics failed for {sym}: {e}")

                    # 3. Knowledge Base
                    try:
                        kb = tijori.get_knowledge_base(slug)
                        stock_data["knowledge_base"] = kb
                    except Exception as e:
                        log.warning(f"Knowledge base failed for {sym}: {e}")

            except Exception as e:
                log.error(f"Error enriching {sym}: {e}")

            enriched_results["stocks"][sym] = stock_data

    out_file = ENRICH_DIR / f"momentum_enriched_{date_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(enriched_results, f, indent=2)

    log.info(f"Momentum enrichment complete. Output saved to {out_file}")
    return enriched_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Momentum stock enrichment")
    parser.add_argument("--date", default="2026-09-03", help="Date YYYY-MM-DD")
    args = parser.parse_args()

    enrich_momentum_stocks(args.date)
