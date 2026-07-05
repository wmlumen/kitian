"""
Capa 1: Router de Contexto Semántico Silencioso.

Clasificación 100% local basada en árboles de decisión por regex.
Sin LLM, sin dependencias externas, sin overhead.
Latencia objetivo: <5 ms. CPU: <1%.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List


@dataclass
class RouteDecision:
    layer: str  # "local" | "cloud" | "hybrid"
    handler: str
    confidence: float
    payload: Dict = field(default_factory=dict)
    reason: str = ""


# ─── Patterns locales (sin IA) ───────────────────────────────────────
_LOCAL_PATTERNS: List[Tuple[re.Pattern, str, float]] = [
    # Recordatorios y agenda
    (re.compile(r"(?:poné|pon|ponme|agendá|agenda|programá|recorda(?:r|me|os)|crea(?:r)?\s+recordatorio|nuevo\s+recordatorio)", re.I), "reminder.create", 0.95),
    (re.compile(r"(?:quitá|eliminá|borrá|borra(?:r)?|cancela(?:r)?)\s+(?:el\s+)?recordatorio", re.I), "reminder.delete", 0.90),
    (re.compile(r"(?:lista(?:r|do|me|os)?|mostra(?:r|me|os)?|ver(?:me|os|lo)?)\s+(?:mis\s+)?(?:recordatorios|tareas|pendientes)", re.I), "reminder.list", 0.92),
    # Archivos y sistema
    (re.compile(r"(?:abrí|abre|abrir|open)\s+(?:el\s+)?(?:archivo|carpeta|directorio|ruta)?\s*[`\"']?([A-Za-z0-9_\-./\\\s]+)[`\"']?", re.I), "files.open", 0.93),
    (re.compile(r"(?:creá|crea(?:r)?|hacé|hacé|nuevo(?:a)?)\s+(?:archivo|carpeta|directorio|proyecto)", re.I), "files.create", 0.94),
    (re.compile(r"(?:borr(?:a|ar|á)|elimin(?:a|ar|á)|delet(?:e|ing))\s+(?:el\s+)?(?:archivo|carpeta)", re.I), "files.delete", 0.92),
    (re.compile(r"(?:mové|mover|mudá)\s+(?:el\s+)?(?:archivo|carpeta)", re.I), "files.move", 0.90),
    (re.compile(r"(?:busc(?:a|ar|á)|encontr(?:a|ar|á)|search)\s+(?:archivo|file|carpeta)", re.I), "files.search", 0.91),
    # Sistema
    (re.compile(r"(?:estado|status|salud|health|carga|uso)", re.I), "system.status", 0.88),
    (re.compile(r"(?:reinici(?:a|ar|á)|restart|apag(?:a|ar|á)|shutdown)", re.I), "system.power", 0.85),
    # Memoria / perfil
    (re.compile(r"(?:perfil|preferencia|preferencias|quien\s+soy|user\s+profile)", re.I), "profile.show", 0.90),
]

# Patrones que REQUIEREN nube (investigación, análisis profundo)
_CLOUD_PATTERNS: List[Tuple[re.Pattern, str, float]] = [
    (re.compile(r"(?:investig(?:a|ar|á)|research|busca(?:r)?\s+(?:información|info|datos|paper|estudio))\s+(?:sobre|de|acerca\s+de|por)?\s*(.+)", re.I), "research.start", 0.92),
    (re.compile(r"(?:consult(?:a|ar|á)|consulta|query|pregunt(?:a|ar|á))\s+(?:a\s+)?(?:la\s+)?nube|external", re.I), "research.start", 0.85),
    (re.compile(r"(?:descarg(?:a|ar|á)|download)\s+(?:archivo|file|repo|documento)", re.I), "cloud.download", 0.80),
]

# Palabras clave ambiguas que disparan fallback
_FUZZY_KEYWORDS: set = {"ayuda", "help", "qué", "que", "como", "cómo", "cuál", "cual", "por qué", "porque"}


class IntentRouter:
    def __init__(self) -> None:
        self._stats: Dict[str, int] = {"local": 0, "cloud": 0, "fallback": 0, "total": 0}
        self._last_route_ms: float = 0.0

    def route(self, command: str) -> RouteDecision:
        t0 = time.perf_counter()
        if not command or not command.strip():
            return RouteDecision("local", "noop", 0.0, reason="empty")

        cmd = command.strip()
        self._stats["total"] += 1

    # 1) Buscar match LOCAL exacto (más específico primero)
        for pattern, handler, confidence in _LOCAL_PATTERNS:
            m = pattern.search(cmd)
            if m:
                payload: Dict = {}
                if m.lastindex and m.group(1):
                    payload["target"] = m.group(1).strip()
                payload["raw"] = cmd
                self._stats["local"] += 1
                self._last_route_ms = (time.perf_counter() - t0) * 1000
                return RouteDecision("local", handler, confidence, payload, reason="regex_local")

    # 2) Buscar match CLOUD explícito
        for pattern, handler, confidence in _CLOUD_PATTERNS:
            m = pattern.search(cmd)
            if m:
                payload = {"query": cmd, "raw": cmd}
                if m.lastindex and m.group(1):
                    payload["query"] = m.group(1).strip()
                self._stats["cloud"] += 1
                self._last_route_ms = (time.perf_counter() - t0) * 1000
                return RouteDecision("cloud", handler, confidence, payload, reason="regex_cloud")

    # 3) Heurística de palabras ambiguas → fallback
        lower = cmd.lower()
        for kw in _FUZZY_KEYWORDS:
            if kw in lower:
                self._stats["fallback"] += 1
                self._last_route_ms = (time.perf_counter() - t0) * 1000
                return RouteDecision("cloud", "fallback.chat", 0.55, {"raw": cmd}, reason="fuzzy_keyword")

    # 4) Por defecto: comando corto (< 40 chars) probablemente local
        if len(cmd) < 40:
            self._stats["local"] += 1
            self._last_route_ms = (time.perf_counter() - t0) * 1000
            return RouteDecision("local", "charlar", 0.70, {"raw": cmd}, reason="short_command")

    # 5) Largo y complejo → probablemente requiera investigación
        self._stats["cloud"] += 1
        self._last_route_ms = (time.perf_counter() - t0) * 1000
        return RouteDecision("cloud", "research.start", 0.60, {"query": cmd}, reason="long_command")

    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def last_route_ms(self) -> float:
        return round(self._last_route_ms, 3)


# Singleton global
_router = IntentRouter()


def get_router() -> IntentRouter:
    return _router


def route_command(command: str) -> RouteDecision:
    return _router.route(command)
