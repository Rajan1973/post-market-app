import uuid
from typing import Dict, List, Any, Optional

class EntityResolver:
    """High-Precision Multi-Tiered Entity Resolution Service for Stocks, Sectors, and Themes."""

    def __init__(self):
        # Tier 1: Official Unambiguous Exchange Tickers (NSE Symbols)
        self.official_nse_symbols: Dict[str, str] = {
            "RELIANCE": "Reliance Industries Ltd",
            "TCS": "Tata Consultancy Services Ltd",
            "INFY": "Infosys Ltd",
            "KEI": "KEI Industries Ltd",
            "POLYCAB": "Polycab India Ltd",
            "HAVELLS": "Havells India Ltd",
            "RRKABEL": "RR Kabel Ltd",
            "BRIGADE": "Brigade Enterprises Ltd",
            "ULTRACEMCO": "UltraTech Cement Ltd",
            "APLAPOLLO": "APL Apollo Tubes Ltd",
            "TATASTEEL": "Tata Steel Ltd",
            "JSWSTEEL": "JSW Steel Ltd",
            "ABB": "ABB India Ltd",
            "BHEL": "Bharat Heavy Electricals Ltd",
            "HAL": "Hindustan Aeronautics Ltd",
            "LTIM": "LTIMindtree Ltd",
            "NTPC": "NTPC Ltd",
            "NH": "Narayana Hrudayalaya Ltd",
            "SKF": "SKF India Ltd",
            "DIX": "Dixon Technologies Ltd",
        }

        # Tier 2: Unambiguous Report Abbreviation -> Official NSE Symbol Mappings
        self.unambiguous_aliases: Dict[str, str] = {
            "KPIT": "KPITTECH",
            "MDL": "MAZDOCK",
            "NYK": "NYKAA",
            "PAY": "PAYTM",
            "PSYS": "PERSISTENT",
            "SONA": "SONACOMS",
            "VED": "VEDL",
            "ZOM": "ZOMATO",
            "FINCABLES": "FINLEXCABL",
            "JSWE": "JSWENERGY",
            "PGC": "POWERGRID",
            "BDL": "BDL",
            "CSL": "COCHINSHIP",
            "CUM": "CUMMINSIND",
            "GOK": "GOKEX",
            "HPL": "HPL",
            "KPR": "KPRMILL",
            "KRS": "KRBL",
            "LAL": "LALPATHLAB",
            "MPH": "MPHASIS",
            "MSUMI": "MOTHERSON",
            "NMD": "NMDC",
            "PBF": "PIGL",
            "RAY": "RAYMOND",
            "SCH": "SCHNEIDER",
            "SIE": "SIEMENS",
            "SIL": "SANGHIIND",
            "SYR": "SYRMA",
            "TOR": "TORNTPHARM",
            "TRIL": "TRIL",
            "UNO": "UNOMINDA",
            "WEL": "WELSPUNLIV"
        }

        # Tier 3: Ambiguous Report Abbreviated Tokens (Candidates for Human / Admin Review Queue)
        self.ambiguous_candidates: Dict[str, List[str]] = {
            "MAX": ["MAXHEALTH", "MFSL"],
            "FOR": ["FORTIS", "FORCEMOT"],
            "MED": ["MEDANTA", "MEDPLUS"],
            "MET": ["METROPOLIS", "METROPOLIS_IND"],
            "SEN": ["SENCO", "SENCORP"],
            "KAY": ["KAYNES", "KAYNES_TECH"],
            "CYI": ["CYIENT", "CYIENTDLM"],
            "GEN": ["GENUSPOWER", "GENUS_ENG"],
            "TPW": ["TORNTPOWER", "TPW_GEN"],
            "APW": ["APARINDS", "APW_IND"],
            "TMK": ["TATAMOTORS", "TMK_IND"],
            "TMY": ["TATAMOTORS", "TMY_IND"],
            "TTN": ["TITAN", "TTN_IND"],
            "AIA": ["AIAENG", "AIA_IND"],
            "AES": ["AES_POWER", "AES_IND"],
            "APR": ["APOLLOTYRE", "APR_IND"],
            "AVA": ["AVANTIFEED", "AVA_IND"],
            "COF": ["COFORGE", "COF_IND"],
            "JSP": ["JSP", "JSP_STEEL"],
            "KAL": ["KALPATPOWR", "KAL_IND"],
            "THY": ["THYROCARE", "THY_IND"],
            "TRI": ["TRIDENT", "TRI_IND"],
            "VIJ": ["VIJAYA", "VIJ_IND"]
        }

        self.unresolved_queue: List[Dict[str, Any]] = []

    def resolve_entity(self, raw_name: str, entity_type: str = "stock", source_report_id: Optional[str] = None) -> Dict[str, Any]:
        cleaned_name = str(raw_name or "").strip().upper().replace("-", "").replace("&", "").replace(" ", "")
        
        # Tier 1: Deterministic Exact Match on Official Exchange Symbol
        if cleaned_name in self.official_nse_symbols:
            official_symbol = cleaned_name
            entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, official_symbol))
            return {
                "tier": 1,
                "resolved": True,
                "entity_id": entity_id,
                "official_symbol": official_symbol,
                "company_name": self.official_nse_symbols[official_symbol],
                "confidence": 1.00,
                "reason": "Exact official NSE symbol match"
            }
        
        # Tier 2: Unambiguous Report Abbreviation -> Official Symbol Mapping
        if cleaned_name in self.unambiguous_aliases:
            official_symbol = self.unambiguous_aliases[cleaned_name]
            entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, official_symbol))
            return {
                "tier": 2,
                "resolved": True,
                "entity_id": entity_id,
                "official_symbol": official_symbol,
                "confidence": 0.95,
                "reason": f"Unambiguous report alias mapping ({cleaned_name} -> {official_symbol})"
            }

        # Tier 3: Ambiguous Ticker Abbreviation -> Review Queue with Candidate Matches
        if cleaned_name in self.ambiguous_candidates:
            candidates = self.ambiguous_candidates[cleaned_name]
            unresolved_record = {
                "id": str(uuid.uuid4()),
                "raw_name": raw_name,
                "cleaned_name": cleaned_name,
                "entity_type": entity_type,
                "tier": 3,
                "candidate_matches": candidates,
                "confidence": 0.60,
                "source_report_id": source_report_id,
                "status": "pending",
                "reason": f"Ambiguous ticker abbreviation with {len(candidates)} candidate matches"
            }
            self.unresolved_queue.append(unresolved_record)
            return {
                "tier": 3,
                "resolved": False,
                "entity_id": None,
                "confidence": 0.60,
                "unresolved_record": unresolved_record
            }

        # Tier 4: Unresolved Unknown Token -> Enqueue in unresolved_entities
        unresolved_record = {
            "id": str(uuid.uuid4()),
            "raw_name": raw_name,
            "cleaned_name": cleaned_name,
            "entity_type": entity_type,
            "tier": 4,
            "candidate_matches": [],
            "confidence": 0.00,
            "source_report_id": source_report_id,
            "status": "pending",
            "reason": "Unknown entity token"
        }
        self.unresolved_queue.append(unresolved_record)
        return {
            "tier": 4,
            "resolved": False,
            "entity_id": None,
            "confidence": 0.00,
            "unresolved_record": unresolved_record
        }
