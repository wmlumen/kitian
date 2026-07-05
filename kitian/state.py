"""Compatibilidad legacy: fachada `SharedState` hacia `kitian_store`.

El único origen real del estado backend es `kitian.store.KitianStore`.
Este módulo NO redefine la clase del store; solo mantiene la API vieja.
"""
from __future__ import annotations

import threading
import time
import copy
from typing import Any, Dict

from kitian.store import kitian_store  # noqa: E402


class SharedState:
    """Fachada legacy que delega a `kitian_store`."""

    def __init__(self) -> None:
        self.status = "Iniciando..."
        self.color = "#00ffff"
        self.info = ""
        self.pulse = 0

        state = kitian_store.get()
        self.visual_data = {
            "kind": state["core"]["mode"].lower(),
            "title": "Listo",
            "summary": "Esperando comando.",
            "metrics": [],
            "sources": [],
            "actions": [],
            "context": [],
            "updated_at": state["updatedAt"],
            "status": state["core"]["status"],
        }
        self.action_log: list = []
        self.COLORES = {
            "hablando": "#00ffcc",
            "activo": "#00ffff",
            "escuchando": "#00cc66",
            "pensando": "#ffcc00",
            "offline": "#ff4444",
            "apagado": "#666666",
        }
        self.emotional_state = dict(state["emotional"])
        self._vis_lock = threading.Lock()
        self._emo_lock = threading.Lock()

    def update_emotional_state_from_metrics(self, metrics: dict) -> None:
        cpu = metrics.get("cpu", 0) or 0
        ram = metrics.get("ram", 0) or 0
        disk = metrics.get("disk", 0) or 0
        fps = metrics.get("fps", 60) or 60

        claridad = max(0.0, min(100.0, 100.0 - (cpu * 0.5 + ram * 0.3 + (100.0 - fps * 2.5))))
        claridad = round(claridad, 1)
        carga = max(0.0, min(100.0, (cpu * 0.6 + ram * 0.4)))
        carga = round(carga, 1)

        if cpu > 90 or ram > 94 or disk > 95:
            riesgo = "Crítico"
        elif cpu > 75 or ram > 80 or disk > 85:
            riesgo = "Alto"
        elif cpu > 55 or ram > 60:
            riesgo = "Medio"
        else:
            riesgo = "Bajo"

        entropia = max(0.0, min(100.0, 15.0 + __import__("random").uniform(-3.0, 8.0) + (carga * 0.15)))
        entropia = round(entropia, 1)

        with self._emo_lock:
            self.emotional_state = {
                "claridad": claridad,
                "carga": carga,
                "riesgo": riesgo,
                "entropia": entropia,
            }
            try:
                kitian_store.merge({"emotional": self.emotional_state})
            except Exception:
                pass

    def get_emotional_state(self) -> dict:
        state = kitian_store.get()
        return dict(state["emotional"])

    def set(self, status, color=None):
        self.status = status
        self.color = color or "#00ffff"
        self.pulse = 0
        kitian_store.merge({"core": {"status": status, "mode": "IDLE" if status == "offline" else "ACTIVE"}})

    def set_info(self, texto):
        self.info = texto
        with self._vis_lock:
            self.visual_data["summary"] = texto
            self.visual_data["updated_at"] = time.strftime("%H:%M:%S")
        kitian_store.merge(
            {
                "core": {"status": "active" if texto else "idle"},
                "inputs": {"lastResponse": texto},
            }
        )

    def set_visual_data(self, payload):
        merged = dict(self.visual_data)
        merged.update(payload or {})
        merged["updated_at"] = time.strftime("%H:%M:%S")
        with self._vis_lock:
            self.visual_data = merged

    def get_visual_data(self):
        with self._vis_lock:
            return copy.deepcopy(self.visual_data)

    def push_action(self, text):
        if not text:
            return
        self.action_log.append(f"{time.strftime('%H:%M:%S')} {text}")
        self.action_log = self.action_log[-12:]

    def get_actions(self):
        return list(self.action_log)

    def get(self):
        return self.status, self.color, self.info

    def tick_pulse(self):
        self.pulse = (self.pulse + 1) % 20
        return self.pulse


state = SharedState()
