"""Estado global canónico de Kitian (frontend + backend)."""
from __future__ import annotations

import threading
import time
import copy
from typing import Any, Dict, Optional, Callable


class KitianStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "core": {
                "connected": False,
                "mode": "IDLE",
                "status": "offline",
                "via": "-",
                "searching": False,
                "latencyMs": None,
            },
            "priorities": {
                "cpu": 0,
                "ram": 0,
                "disk": 0,
                "netDown": 0,
                "netUp": 0,
            },
            "memory": {
                "interactions": 0,
                "keywords": [],
                "activeGoal": None,
                "recent": [],
            },
            "inputs": {
                "lastCommand": None,
                "lastResponse": None,
                "voiceMode": "PUNCTUAL",
                "listening": False,
            },
            "director": {
                "mode": 0,
                "label": "Manual",
                "lastExplanation": None,
                "audit": [],
            },
            "goalTree": {
                "active": None,
                "branches": [],
                "status": "IDLE",
            },
            "emotional": {
                "claridad": 85.0,
                "carga": 15.0,
                "riesgo": "Bajo",
                "entropia": 20.0,
            },
            "perception": {
                "motion": 0,
                "gesture": "NONE",
                "cursor": None,
            },
            "voice": {
                "wakewordActive": False,
                "wakewordDetected": False,
                "pttActive": False,
            },
            "updatedAt": time.strftime("%H:%M:%S"),
        }
        self._listeners: list = []

    # ----- snapshot / merge -----

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def merge(self, patch: Dict[str, Any]) -> None:
        with self._lock:
            for key, value in patch.items():
                if key in self._state and isinstance(value, dict) and isinstance(self._state[key], dict):
                    merged = copy.deepcopy(self._state[key])
                    merged.update(value)
                    self._state[key] = merged
                else:
                    self._state[key] = copy.deepcopy(value)
            self._state["updatedAt"] = time.strftime("%H:%M:%S")
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(self._state)
            except Exception as e:
                log = __import__("logging").getLogger("kitian.store")
                log.warning("store listener error: %s", e, exc_info=True)

    def reset(self) -> None:
        self.merge(
            {
                "core": {
                    "connected": False,
                    "mode": "IDLE",
                    "status": "offline",
                    "via": "-",
                    "searching": False,
                    "latencyMs": None,
                },
                "priorities": {"cpu": 0, "ram": 0, "disk": 0, "netDown": 0, "netUp": 0},
                "memory": {"interactions": 0, "keywords": [], "activeGoal": None, "recent": []},
                "inputs": {
                    "lastCommand": None,
                    "lastResponse": None,
                    "voiceMode": "PUNCTUAL",
                    "listening": False,
                },
                "director": {"mode": 0, "label": "Manual", "lastExplanation": None, "audit": []},
                "goalTree": {"active": None, "branches": [], "status": "IDLE"},
                "emotional": {"claridad": 85.0, "carga": 15.0, "riesgo": "Bajo", "entropia": 20.0},
                "perception": {"motion": 0, "gesture": "NONE", "cursor": None},
                "voice": {"wakewordActive": False, "wakewordDetected": False, "pttActive": False},
            }
        )

    # ----- helpers -----

    def on_update(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(fn)

    def snapshot_from_profile(self, profile: Dict[str, Any]) -> None:
        patch: Dict[str, Any] = {"memory": {}}
        with self._lock:
            current = copy.deepcopy(self._state["memory"])
        interactions = profile.get("interactions", current.get("interactions", 0))
        top_keywords = profile.get("top_keywords", [])
        keywords = [k[0] for k in top_keywords] if top_keywords else current.get("keywords", [])
        active_goal = profile.get("active_goal", current.get("activeGoal"))
        recent = current.get("recent", [])
        patch["memory"] = {
            "interactions": interactions,
            "keywords": keywords,
            "activeGoal": active_goal,
            "recent": recent,
        }
        self.merge(patch)


kitian_store = KitianStore()
