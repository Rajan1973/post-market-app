import uuid
from typing import Dict, List, Any, Optional

class EntityResolver:
    """Multi-tiered Entity Resolution Service for Stocks, Sectors, and Themes."""

    def __init__(self):
        # Known stock map (Symbol/Alias -> Mock UUID for local processing)
        tickers = [
            "RELIANCE", "TCS", "INFY", "KEI", "POLYCAB", "FINCABLES", "HAVELLS", "RRKABEL",
            "BRIGADE", "ULTRACEMCO", "APLAPOLLO", "TATASTEEL", "TATA STEEL", "JSWSTEEL",
            "ABB", "AES", "AIA", "APR", "APW", "AVA", "BDL", "BHEL", "COF", "CSL", "CUM",
            "CYI", "DIX", "FOR", "GEN", "GOK", "HAL", "HPL", "JSP", "JSWE", "KAL", "KAY",
            "KPIT", "KPR", "KRS", "LAL", "LTIM", "MAX", "MDL", "MED", "MET", "MPH", "MSUMI",
            "NH", "NMD", "NTPC", "NYK", "PAY", "PBF", "PGC", "PSYS", "RAY", "SCH", "SEN",
            "SIE", "SIL", "SKF", "SONA", "SYR", "THY", "TMK", "TMX", "TMY", "TOR", "TPW",
            "TRI", "TRIL", "TTN", "UNO", "VED", "VIJ", "WEL", "ZOM"
        ]
        self.known_mappings: Dict[str, str] = {
            t: str(uuid.uuid5(uuid.NAMESPACE_DNS, t.replace(" ", ""))) for t in tickers
        }
        self.unresolved_queue: List[Dict[str, Any]] = []

    def resolve_entity(self, raw_name: str, entity_type: str = "stock", source_report_id: Optional[str] = None) -> Dict[str, Any]:
        cleaned_name = str(raw_name or "").strip().upper().replace("-", "").replace("&", "")
        
        # Tier 1: Deterministic Exact Match
        if cleaned_name in self.known_mappings:
            return {
                "tier": 1,
                "resolved": True,
                "entity_id": self.known_mappings[cleaned_name],
                "confidence": 1.00,
                "matched_alias": cleaned_name
            }
        
        # Tier 2: High-Confidence Contextual Alias Match
        for known_name, entity_id in self.known_mappings.items():
            if known_name in cleaned_name or cleaned_name in known_name:
                return {
                    "tier": 2,
                    "resolved": True,
                    "entity_id": entity_id,
                    "confidence": 0.90,
                    "matched_alias": known_name
                }
        
        # Tier 4: Unresolved entity -> Enqueue in unresolved_entities
        unresolved_record = {
            "id": str(uuid.uuid4()),
            "raw_name": raw_name,
            "entity_type": entity_type,
            "candidate_matches": [],
            "confidence": 0.00,
            "source_report_id": source_report_id,
            "status": "pending"
        }
        self.unresolved_queue.append(unresolved_record)
        
        return {
            "tier": 4,
            "resolved": False,
            "entity_id": None,
            "confidence": 0.00,
            "unresolved_record": unresolved_record
        }
