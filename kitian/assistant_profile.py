"""Perfil ejecutivo de Kitian: preferencias del usuario y adaptación de respuestas."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


PROFILE_PATH = Path(__file__).with_name("assistant_profile.json")


def _load() -> Dict[str, Any]:
    try:
        if PROFILE_PATH.exists():
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {
        "user": {
            "name": "Usuario",
            "preferred_language": "es",
            "interaction_mode": "voice_and_text",  # voice | text | voice_and_text
            "communication_style": "ejecutivo",  # informal | ejecutivo | tecnico
        },
        "preferences": {
            "apply_learning": True,
            "proactive_recommendations": False,
            "default_response_length": "balanced",  # short | balanced | detailed
            "open_calendar_on_start": False,
        },
        "memory": {
            "todos": [],
            "recent_goals": [],
            "frequency_keywords": {},
            "last_interactions": [],
        },
        "systems": {
            "cognitive_recognition": False,
            "calendar_system": None,  # google | local | None
            "reminders_enabled": False,
        },
        "meta": {
            "created_at": time.time(),
            "updated_at": time.time(),
        },
    }


def _save(data: Dict[str, Any]) -> None:
    try:
        PROFILE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        data["meta"]["updated_at"] = time.time()
    except Exception:
        pass


class AssistantProfile:
    """Interfaz principal para el perfil ejecutivo de Kitian."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = _load()

    # -------- Lectura / escritura segura --------

    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in path.split("."):
            if not isinstance(cur, dict):
                return default
            cur = cur.get(part, default)
        return cur

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        cur = self._data
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value
        _save(self._data)

    # -------- Preferencias del usuario --------

    @property
    def language(self) -> str:
        return str(self.get("user.preferred_language", "es"))

    @property
    def interaction_mode(self) -> str:
        return str(self.get("user.interaction_mode", "voice_and_text"))

    @property
    def communication_style(self) -> str:
        return str(self.get("user.communication_style", "ejecutivo"))

    @property
    def response_length(self) -> str:
        return str(self.get("preferences.default_response_length", "balanced"))

    def set_language(self, lang: str) -> None:
        self.set("user.preferred_language", lang)

    def set_interaction_mode(self, mode: str) -> None:
        self.set("user.interaction_mode", mode)

    def set_communication_style(self, style: str) -> None:
        self.set("user.communication_style", style)

    # -------- Memoria de uso --------

    def remember_todo(self, todo: Dict[str, Any]) -> None:
        todos: List[Dict[str, Any]] = list(self.get("memory.todos", []))
        todos.append({
            "text": str(todo.get("text", "")),
            "created_at": time.time(),
            "done": bool(todo.get("done", False)),
        })
        if len(todos) > 100:
            todos = todos[-100:]
        self.set("memory.todos", todos)

    def get_open_todos(self) -> List[Dict[str, Any]]:
        todos = self.get("memory.todos", [])
        return [t for t in todos if not t.get("done")]

    def mark_todo_done(self, index: int) -> Optional[Dict[str, Any]]:
        todos: List[Dict[str, Any]] = list(self.get("memory.todos", []))
        open_todos = [i for i, t in enumerate(todos) if not t.get("done")]
        if not open_todos or index < 0 or index >= len(open_todos):
            return None
        pos = open_todos[index]
        todos[pos]["done"] = True
        todo = todos[pos]
        self.set("memory.todos", todos)
        return todo

    def log_interaction(self, kind: str, text: str, extra: Optional[Dict[str, Any]] = None) -> None:
        hist: List[Dict[str, Any]] = list(self.get("memory.last_interactions", []))
        hist.append({
            "kind": kind,
            "text": text,
            "ts": time.time(),
            "extra": extra or {},
        })
        if len(hist) > 200:
            hist = hist[-200:]
        self.set("memory.last_interactions", hist)
        # Refuerzo simple de frecuencia
        for word in text.split():
            w = word.lower().strip().strip(".,!?")
            if len(w) < 3:
                continue
            freqs: Dict[str, int] = dict(self.get("memory.frequency_keywords", {}))
            freqs[w] = int(freqs.get(w, 0)) + 1
            self.set("memory.frequency_keywords", freqs)

    # -------- Diagnóstico rápido --------

    def summary(self) -> Dict[str, Any]:
        open_todos = len(self.get_open_todos())
        interactions = len(self.get("memory.last_interactions", []))
        settings_count = len(self._data.get("preferences", {})) + len(self._data.get("user", {}))
        last_interactions = list(self.get("memory.last_interactions", []))[-8:]
        frequency_keywords = sorted(
            ((k, int(v)) for k, v in self.get("memory.frequency_keywords", {}).items()),
            key=lambda x: x[1],
            reverse=True,
        )[:8]
        active_goal = (self.get("memory.recent_goals", []) or [{}])[-1].get("text")
        return {
            "language": self.language,
            "interaction_mode": self.interaction_mode,
            "style": self.communication_style,
            "response_length": self.response_length,
            "open_todos": open_todos,
            "interactions": interactions,
            "settings_count": settings_count,
            "profile_path": str(PROFILE_PATH),
            "last_interactions": last_interactions,
            "top_keywords": frequency_keywords,
            "active_goal": active_goal,
        }
