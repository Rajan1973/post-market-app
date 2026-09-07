import uuid
from typing import Dict, List, Any, Optional

class EntityResolver:
    """First-pass Entity Resolution Service."""

    def __init__(self):
        # Known stock map (Symbol/Alias -> Mock UUID for Phase 1 local processing)
        self.known_mappings: Dict[str, str] = {
            "RELIANCE": str(uuid.uuid5(uuid.NAMESPACE_DNS, "RELIANCE")),
            "TCS": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TCS")),
            "INFY": str(uuid.uuid5(uuid.NAMESPACE_DNS, "INFY")),
            "KEI": str(uuid.uuid5(uuid.NAMESPACE_DNS, "KEI")),
            "POLYCAB": str(uuid.uuid5(uuid.NAMESPACE_DNS, "POLYCAB")),
            "FINCABLES": str(uuid.uuid5(uuid.NAMESPACE_DNS, "FINCABLES")),
            "HAVELLS": str(uuid.uuid5(uuid.NAMESPACE_DNS, "HAVELLS")),
            "RRKABEL": str(uuid.uuid5(uuid.NAMESPACE_DNS, "RRKABEL")),
            "BRIGADE": str(uuid.uuid5(uuid.NAMESPACE_DNS, "BRIGADE")),
            "ULTRACEMCO": str(uuid.uuid5(uuid.NAMESPACE_DNS, "ULTRACEMCO")),
            "APLAPOLLO": str(uuid.uuid5(uuid.NAMESPACE_DNS, "APLAPOLLO")),
            "TATASTEEL": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TATASTEEL")),
            "TATA STEEL": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TATASTEEL")),
            "JSWSTEEL": str(uuid.uuid5(uuid.NAMESPACE_DNS, "JSWSTEEL")),
        }
        self.unresolved_queue: List[Dict[str, Any]] = []

    def resolve_entity(self, raw_name: str, entity_type: str = "stock", source_report_id: Optional[str] = None) -> Dict[str, Any]:
        cleaned_name = str(raw_name or "").strip().upper().replace("-", "").replace("&", "")
        
        # Exact match in known mappings
        if cleaned_name in self.known_mappings:
            return {
                "resolved": True,
                "entity_id": self.known_mappings[cleaned_name],
                "confidence": 1.00,
                "matched_alias": cleaned_name
            }
        
        # Try finding partial ticker match
        for known_name, entity_id in self.known_mappings.items():
            if known_name in cleaned_name or cleaned_name in known_name:
                return {
                    "resolved": True,
                    "entity_id": entity_id,
                    "confidence": 0.85,
                    "matched_alias": known_name
                }
        
        # Unresolved entity -> Enqueue in unresolved_entities
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
            "resolved": False,
            "entity_id": None,
            "confidence": 0.00,
            "unresolved_record": unresolved_record
        }
