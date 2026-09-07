import abc
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class IntermediateReport:
    type: str # eod, sector
    title: str
    date: str
    headline: str = ""
    standfirst: str = ""
    subtitle: str = ""
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    source_file: str = ""
    source_hash: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    entities: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: {"stocks": [], "sectors": [], "themes": []})
    metrics: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: {"market": [], "stocks": [], "sectors": [], "flows": [], "fno": [], "flexible": []})
    narrative: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report": {
                "type": self.type,
                "title": self.title,
                "date": self.date,
                "headline": self.headline,
                "standfirst": self.standfirst,
                "subtitle": self.subtitle,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "source_file": self.source_file,
                "source_hash": self.source_hash
            },
            "sections": self.sections,
            "entities": self.entities,
            "metrics": self.metrics,
            "narrative": self.narrative,
            "events": self.events,
            "signals": self.signals,
            "relationships": self.relationships
        }

class BaseReportParser(abc.ABC):
    """Abstract base report parser interface."""

    def __init__(self, file_path: Path, sha256_hash: str):
        self.file_path = file_path
        self.sha256_hash = sha256_hash
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            self.content = f.read()

    @abc.abstractmethod
    def parse(self) -> IntermediateReport:
        """Parse raw HTML into CommonIntermediateFormat."""
        pass
