"""
Sistema de intención vivo (goal tree) para Kitian.

Convierte comandos del usuario en objetivos estructurados, con jerarquías,
estados y trazabilidad. Usa `MemoryEngine` como backend.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, List, Optional

from .memory_engine import MemoryEngine, GoalNode


class GoalTree:
    def __init__(self, engine: Optional[MemoryEngine] = None) -> None:
        self._engine = engine or MemoryEngine()
        self._lock = threading.Lock()
        self._active_goal_id: Optional[str] = None

    # ── Intake ──────────────────────────────────────────────────────
    def interpret(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        created: List[Dict[str, Any]] = []

        def _save(kind: str, pattern: str) -> Optional[str]:
            m = re.search(pattern, text, re.IGNORECASE)
            if not m:
                return None
            gid = self._engine.add_goal(kind=kind, tags=["auto"]).id
            if kind == "buscar" and m.group(1):
                self._engine.update_goal(gid, text=f"Buscar: {m.group(1)}")
            return gid

        patterns = [
            ("crear", r"cre[a-z]*\s+(.+)"),
            ("abrir", r"abre?[r]?\s+(.+)"),
            ("investigar", r"investig[a-z]*\s+(.+)"),
            ("buscar", r"busca[r]?\s+(.+)"),
            ("programar", r"program[ae]?[r]?\s+(.+)"),
            ("recordar", r"recuerd[a-z]*\s+(.+)"),
            ("analizar", r"analiz[a-z]*\s+(.+)"),
        ]

        for kind, pat in patterns:
            gid = _save(kind, pat)
            if gid:
                created.append({"id": gid, "kind": kind})
                break

        if not created:
            gid = self._engine.add_goal("explorar", text=text[:120], tags=["fallback"]).id
            created.append({"id": gid, "kind": "explorar"})

        node = self._engine.get_goal(created[-1]["id"])
        self._set_active(created[-1]["id"])
        self._engine.record(kind="goal", text=text, meta={"goal_id": created[-1]["id"], "created": created})
        return {"created": created, "active": self._engine.get_goal(self._active_goal_id)}

    def advance(self, gid: str, progress: Optional[int] = None,
                status: Optional[str] = None, text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # progress + status sin misalignment total
        updated = self._engine.update_goal(gid, progress=progress, status=status, text=text)
        if updated:
            self._engine.record(kind="goal_update", text="", meta={"goal_id": gid})
        return self._engine.get_goal(gid)

    def branch(self, parent_id: str, text: str) -> Optional[Dict[str, Any]]:
        node = self._engine.add_goal(text, parent_id=parent_id, tags=["branch"])
        self._engine.record(kind="goal_branch", text=text, meta={"parent_id": parent_id, "child_id": node.id})
        return self._engine.get_goal(node.id)

    def complete(self, gid: Optional[str] = None) -> Optional[Dict[str, Any]]:
        target = gid or self._active_goal_id
        if not target:
            return None
        return self.advance(target, status="completed", progress=100)

    # ── Query ───────────────────────────────────────────────────────
    def active(self) -> Optional[Dict[str, Any]]:
        if self._active_goal_id:
            g = self._engine.get_goal(self._active_goal_id)
            if g and g.get("status") == "completed":
                self._active_goal_id = None
                return None
            return g
        return None

    def list_goals(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self._engine.list_goals(status=status, limit=limit)

    def get_goal(self, gid: str) -> Optional[Dict[str, Any]]:
        return self._engine.get_goal(gid)

    def snapshot(self) -> Dict[str, Any]:
        return self._engine.snapshot()

    # ── Internals ───────────────────────────────────────────────────
    def _set_active(self, gid: str) -> None:
        with self._lock:
            self._active_goal_id = gid

    def _set_active_explicit(self, gid: str) -> None:
        with self._lock:
            if gid in self._engine.goals:
                self._active_goal_id = gid


# ── Singleton ────────────────────────────────────────────────────
_goal_tree_singleton: Optional[GoalTree] = None
_goal_tree_lock = threading.Lock()

def get_goal_tree() -> GoalTree:
    global _goal_tree_singleton
    if _goal_tree_singleton is None:
        with _goal_tree_lock:
            if _goal_tree_singleton is None:
                _goal_tree_singleton = GoalTree()
    return _goal_tree_singleton
