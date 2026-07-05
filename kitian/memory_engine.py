"""
Motor de memoria operativa para Kitian.

Núcleo de memoria viva multi-capa:
- working_memory: buffer circular de interacciones recientes (tope N)
- semantic_index: índice de palabras clave con conteo y recencia
- goal_log: lista de objetivos y avances recientes

Todo en memoria, thread-safe.
No requiere bases externas.
"""
from __future__ import annotations

import threading
import time
from collections import deque, Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEvent:
    kind: str
    text: str
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalNode:
    id: str
    text: str
    status: str = "pending"  # pending | active | completed | failed
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    progress: int = 0
    tags: List[str] = field(default_factory=list)


class MemoryEngine:
    def __init__(self, *, working_capacity: int = 120, goal_limit: int = 40) -> None:
        self._lock = threading.Lock()
        self.working_memory: deque[MemoryEvent] = deque(maxlen=working_capacity)
        self.semantic_index: Counter = Counter()
        self.goals: Dict[str, GoalNode] = {}
        self._goal_order: List[str] = []
        self._goal_seq = 0
        self.goal_limit = goal_limit

    # ── Working memory ──────────────────────────────────────────────
    def record(self, kind: str, text: str, **meta: Any) -> MemoryEvent:
        ev = MemoryEvent(kind=kind, text=text, meta=meta)
        with self._lock:
            self.working_memory.append(ev)
            for word in self._tokenize(text):
                self.semantic_index[word] += 1
        return ev

    def recent(self, n: int = 12, *, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(reversed(self.working_memory))
        if kind:
            items = [i for i in items if i.kind == kind]
        return [self._event_to_dict(i) for i in items[:n]]

    def top_keywords(self, n: int = 8) -> List[tuple[str, int]]:
        with self._lock:
            return self.semantic_index.most_common(n)

    # ── Goals ───────────────────────────────────────────────────────
    def add_goal(self, text: str, *, parent_id: Optional[str] = None, tags: Optional[List[str]] = None) -> GoalNode:
        with self._lock:
            self._goal_seq += 1
            gid = f"G{self._goal_seq}"
            node = GoalNode(id=gid, text=text, parent_id=parent_id, tags=tags or [])
            self.goals[gid] = node
            self._goal_order.append(gid)
            if len(self._goal_order) > self.goal_limit:
                drop = self._goal_order.pop(0)
                self.goals.pop(drop, None)
            if parent_id and parent_id in self.goals:
                self.goals[parent_id].children.append(gid)
            return node

    def update_goal(self, gid: str, *, status: Optional[str] = None, progress: Optional[int] = None,
                    text: Optional[str] = None) -> Optional[GoalNode]:
        with self._lock:
            node = self.goals.get(gid)
            if not node:
                return None
            if status is not None:
                node.status = status
            if progress is not None:
                node.progress = max(0, min(100, progress))
            if text is not None:
                node.text = text
            node.updated_at = time.time()
            return node

    def get_goal(self, gid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            node = self.goals.get(gid)
            return self._goal_to_dict(node) if node else None

    def list_goals(self, *, status: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        with self._lock:
            nodes = [self.goals[gid] for gid in self._goal_order if gid in self.goals]
        if status:
            nodes = [n for n in nodes if n.status == status]
        return [self._goal_to_dict(n) for n in nodes[:limit]]

    # ── Snapshot ────────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "working_memory": [self._event_to_dict(e) for e in list(self.working_memory)[-20:]],
                "top_keywords": self.semantic_index.most_common(10),
                "goals_open": [self.goals[g].id for g in self._goal_order if self.goals[g].status != "completed"],
                "goals_recent": [self._goal_to_dict(self.goals[g]) for g in self._goal_order[-8:] if g in self.goals],
            }

    # ── Internals ───────────────────────────────────────────────────
    @staticmethod
    def _tokenize(text: str):
        text = "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace())
        return [w for w in text.split() if len(w) > 3]

    @staticmethod
    def _event_to_dict(ev: MemoryEvent) -> Dict[str, Any]:
        return {"kind": ev.kind, "text": ev.text, "ts": ev.ts, "meta": ev.meta}

    @staticmethod
    def _goal_to_dict(node: Optional[GoalNode]) -> Dict[str, Any]:
        if not node:
            return {}
        return {
            "id": node.id,
            "text": node.text,
            "status": node.status,
            "progress": node.progress,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "parent_id": node.parent_id,
            "children": node.children,
            "tags": node.tags,
        }


# ── Singleton ────────────────────────────────────────────────────
_memory_singleton: Optional[MemoryEngine] = None
_memory_lock = threading.Lock()

def get_memory() -> MemoryEngine:
    global _memory_singleton
    if _memory_singleton is None:
        with _memory_lock:
            if _memory_singleton is None:
                _memory_singleton = MemoryEngine()
    return _memory_singleton
