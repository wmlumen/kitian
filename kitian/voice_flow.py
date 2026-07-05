"""Backend unificado de voz de Kitian.

Responsabilidades:
- TTS / STT unificados.
- Normalización básica de texto.
- Pipeline de voz: escuchar -> interpretar -> ejecutar -> responder.
- Integración HTTP para `/api/voice/interact`.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from kitian.audio import (
    hablar,
    escuchar_comando,
    escuchar_continuo,
    transcribir_local,
    load_whisper,
)

log = logging.getLogger("kitian")


class VoiceFlow:
    """Interfaz mínima unificada para voz."""

    def __init__(self, tts_enabled: bool = True, default_response_type: str = "balanced") -> None:
        self.tts_enabled = bool(tts_enabled)
        self.default_response_type = default_response_type or "balanced"

    def speak(self, texto: str, blocking: bool = True) -> bool:
        if not self.tts_enabled:
            log.debug("Voz desactivada (tts_enabled=False): %s", texto[:120])
            return False
        try:
            hablar(texto, blocking=blocking)
            return True
        except Exception as e:
            log.warning("VoiceFlow.speak error: %s", e)
            return False

    def listen(self, timeout: int = 8) -> Optional[str]:
        try:
            texto = escuchar_comando(timeout=timeout)
            return texto
        except Exception as e:
            log.warning("VoiceFlow.listen error: %s", e)
            return None

    @staticmethod
    def normalize(text: str) -> str:
        texto = (text or "").strip()
        texto = re.sub(r"\s+", " ", texto)
        texto = texto.strip(".,;:!?¡¿ ")
        return texto.lower()

    def _route_improvement(self, comando: str) -> Optional[str]:
        """Heurísticas rápidas para mejoras frecuentes.
        Si no aplica, devuelve None para usar el pipeline estándar."""
        if not comando:
            return None
        cl = comando.lower()
        if any(pref in cl for pref in ["mejora", "mejorar", "mejoras"]):
            if re.search(r"\brespuesta\b", cl):
                return "Cambiando a respuestas más directas."
            if re.search(r"\bforma\b|\bestilo\b", cl):
                return "Ajustando estilo de respuesta."
            if re.search(r"\bvelocidad\b|\brapidez\b|\btiempo\b", cl):
                return "Reduciendo verbosidad y espera."
        if any(pref in cl for pref in ["traduce", "traducción", "traduceme"]):
            return self._translate_hint(comando)
        return None

    def _translate_hint(self, comando: str) -> Optional[str]:
        return None

    def process_improvement_command(self, comando: str) -> str:
        texto = self.normalize(comando)
        mejora = self._route_improvement(texto)
        if mejora:
            try:
                self._apply_improvement_preferences(texto)
            except Exception:
                pass
            return mejora
        return self.standard_process(comando)

    def _apply_improvement_preferences(self, comando: str) -> None:
        try:
            from kitian.preference_engine import PreferenceEngine
            from kitian.assistant_profile import AssistantProfile
            profile = AssistantProfile()
            pref = PreferenceEngine(profile)
            cl = comando.lower()
            if any(p in cl for p in ["mejora la respuesta", "respuestas más directas", "menos largas"]):
                pref.apply({"style": "concise"})
            if any(p in cl for p in ["tono más formal", "formal", "serio"]):
                pref.apply({"tone": "formal"})
            if any(p in cl for p in ["tono más relajado", "informal", "cercano"]):
                pref.apply({"tone": "informal"})
        except Exception as e:
            log.debug("apply_improvement_preferences warning: %s", e)

    def standard_process(self, comando: str) -> str:
        try:
            respuesta = _dispatch_improvement_or_default(comando)
        except Exception as e:
            log.warning("VoiceFlow.standard_process error: %s", e)
            respuesta = None

        if not respuesta:
            respuesta = "No pude ejecutar la instrucción por voz."

        return self._finalize(comando, respuesta)

    def _finalize(self, comando: str, respuesta: str) -> str:
        try:
            self.speak(respuesta, blocking=False)
        except Exception:
            pass
        try:
            from kitian.state import state
            state.set_info(respuesta)
        except Exception:
            pass
        return respuesta

    def process_interaction(self, comando: str, respuesta: str) -> None:
        self.speak(respuesta)

    def listen_and_process(self, timeout: int = 8) -> str:
        texto = self.listen(timeout=timeout)
        if not texto:
            respuesta = "No escuché nada. Podés repetir?"
            self._finalize("", respuesta)
            return respuesta
        try:
            self._log_voice("listened", texto)
        except Exception:
            pass
        return self.process_improvement_command(texto)

    @staticmethod
    def _log_voice(kind: str, text: str) -> None:
        try:
            from kitian.assistant_profile import AssistantProfile
            from kitian.state import state
            profile = AssistantProfile()
            profile.log_interaction(kind=kind, text=text)
            state.set_info(f"[voz] {text}")
        except Exception:
            pass


def _dispatch_improvement_or_default(comando: str) -> Optional[str]:
    if not comando:
        return None
    cl = comando.strip()

    try:
        from kitian.intent_router import get_router
        route = get_router().route(cl)
        if route.handler in {"reminder.create", "reminder.delete", "reminder.list"}:
            from kitian.dispatcher import _handle_reminder_command
            return _handle_reminder_command(cl, route)
    except Exception:
        pass

    try:
        from kitian.dispatcher import dispatcher_local
        respuesta = dispatcher_local(cl)
        if respuesta:
            return respuesta
    except Exception:
        pass

    try:
        from kitian.goal_tree import get_goal_tree
        interpretacion = get_goal_tree().interpret(cl)
        sugerencias = interpretacion.get("suggested_goals") if isinstance(interpretacion, dict) else None
        if sugerencias:
            return "Interpreté: " + ", ".join(str(x) for x in sugerencias[:3])
    except Exception:
        pass

    return None


VOICE_FLOW = VoiceFlow()


def listen_once(timeout: int = 8) -> Optional[str]:
    return VOICE_FLOW.listen(timeout=timeout)


def speak_text(texto: str, blocking: bool = True) -> bool:
    return VOICE_FLOW.speak(texto, blocking=blocking)


def process_voice(texto: str) -> str:
    return VOICE_FLOW.process_improvement_command(texto)


def listen_and_process(timeout: int = 8) -> str:
    return VOICE_FLOW.listen_and_process(timeout=timeout)
