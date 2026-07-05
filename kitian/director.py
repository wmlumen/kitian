"""
Modo Director para Kitian.
Niveles: 0 manual, 1 sugerido, 2 semiautónomo, 3 autónomo.
Incluye sistema de explicabilidad por acción.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DirectorAction:
    kind: str
    summary: str
    rationale: str
    cost: str
    reversible: bool
    data: Dict[str, Any] = field(default_factory=dict)


class Director:
    LEVELS = {
        0: "Manual",
        1: "Sugerido",
        2: "Semiautonomo",
        3: "Autonomo",
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.mode: int = 0
        self.audit: List[DirectorAction] = []
        self.max_audit = 80
        self.last_explanation: Optional[str] = None

    def set_mode(self, mode: int) -> Dict[str, Any]:
        with self._lock:
            self.mode = max(0, min(3, int(mode)))
        return self.status()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "mode": self.mode,
                "label": self.LEVELS.get(self.mode, "?"),
                "last_explanation": self.last_explanation,
            }

    def explain(self, summary: str, rationale: str, cost: str = "bajo", reversible: bool = True,
                data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        act = DirectorAction(
            kind="explain",
            summary=summary,
            rationale=rationale,
            cost=cost,
            reversible=reversible,
            data=data or {},
        )
        with self._lock:
            self.last_explanation = f"{summary} | {rationale} | costo: {cost}"
            self.audit.append(act)
            if len(self.audit) > self.max_audit:
                self.audit = self.audit[-self.max_audit:]
        return {
            "mode": self.mode,
            "label": self.LEVELS.get(self.mode, "?"),
            "accepted": self.mode >= 2,
            "summary": summary,
            "rationale": rationale,
            "cost": cost,
            "reversible": reversible,
        }

    def audit_log(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(reversed(self.audit[-limit:]))
        return [
            {
                "kind": i.kind,
                "summary": i.summary,
                "rationale": i.rationale,
                "cost": i.cost,
                "reversible": i.reversible,
                "data": i.data,
            }
            for i in items
        ]


# ── Singleton ────────────────────────────────────────────────────
_director_singleton: Optional[Director] = None
_director_lock = threading.Lock()


def get_director() -> Director:
    global _director_singleton
    if _director_singleton is None:
        with _director_lock:
            if _director_singleton is None:
                _director_singleton = Director()
    return _director_singleton
