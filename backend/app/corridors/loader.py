"""Load a corridor rule pack (YAML). Every value keeps its source and confidence."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import yaml

from app.money import D

CORRIDOR_DIR = Path(__file__).parent
CONFIDENCE_LEVELS = {"official", "secondary", "field", "assumption", "sample"}


@dataclass(frozen=True)
class Param:
    name: str
    value: Decimal
    confidence: str
    source: str
    note: str = ""

    @property
    def is_estimate(self) -> bool:
        return self.confidence != "official"


@dataclass
class Corridor:
    id: str
    name: str
    home_currency: str
    host_currency: str
    vehicle_currency: str
    reviewed: str
    params: dict[str, Param]
    blocked_memo_terms: list[str] = field(default_factory=list)

    def v(self, name: str) -> Decimal:
        """Value of a parameter. Raises KeyError for unknown names (fail loudly)."""
        return self.params[name].value

    def i(self, name: str) -> int:
        return int(self.params[name].value)

    def meta(self, name: str) -> dict:
        p = self.params[name]
        return {"value": str(p.value), "confidence": p.confidence, "source": p.source, "note": p.note}


def load_corridor(corridor_id: str = "bd_cn") -> Corridor:
    path = CORRIDOR_DIR / f"{corridor_id}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    params: dict[str, Param] = {}
    for name, spec in raw["params"].items():
        confidence = spec["confidence"]
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"{name}: unknown confidence '{confidence}'")
        params[name] = Param(
            name=name,
            value=D(str(spec["value"])),
            confidence=confidence,
            source=spec["source"],
            note=spec.get("note", ""),
        )
    return Corridor(
        id=raw["id"],
        name=raw["name"],
        home_currency=raw["home_currency"],
        host_currency=raw["host_currency"],
        vehicle_currency=raw["vehicle_currency"],
        reviewed=raw["reviewed"],
        params=params,
        blocked_memo_terms=[t.lower() for t in raw.get("blocked_memo_terms", [])],
    )
