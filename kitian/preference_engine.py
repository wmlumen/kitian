"""Reconocimiento de preferencias y adaptación de Kitian."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from kitian.assistant_profile import AssistantProfile


class PreferenceEngine:
    """Analiza interacciones y adapta el comportamiento del asistente."""

    def __init__(self, profile: Optional[AssistantProfile] = None) -> None:
        self.profile = profile or AssistantProfile()
        self._synced = False

    # ------------------------------------------------------------------
    # Análisis de interacciones
    # ------------------------------------------------------------------

    def dominant_keywords(self, limit: int = 20) -> List[tuple]:
        freqs: Dict[str, int] = self.profile.get("memory.frequency_keywords", {}) or {}
        return Counter(freqs).most_common(limit)

    def likely_current_focus(self) -> str:
        keywords = self.dominant_keywords(5)
        if not keywords:
            return ""
        return " ".join([w for w, _ in keywords])

    # ------------------------------------------------------------------
    # Adaptación automática de respuestas
    # ------------------------------------------------------------------

    def suggest_response_length(self) -> str:
        style = self.profile.communication_style
        if style == "ejecutivo":
            return "balanced"
        if style == "tecnico":
            return "detailed"
        return "balanced"

    def adapt_command_response(self, raw_text: str, response_type_hint: Optional[str] = None) -> str:
        """Responde al usuario con tono ajustado a su estilo comunicativo."""
        style = self.profile.communication_style
        response_type = response_type_hint or self.suggest_response_length()
        text = raw_text.strip()

        if not text:
            return "Listo."

        if style == "ejecutivo":
            prefixes = [
                "Avanzamos: ",
                "Entendido. ",
                "Confirmo: ",
                "Así quedó: ",
            ]
            import random

            prefix = prefixes[len(text) % len(prefixes)]
            if response_type == "short" and len(text) > 140:
                text = text[:140] + "..."
            return prefix + text

        if style == "tecnico":
            return text

        # informal
        return text

    # ------------------------------------------------------------------
    # Aprendizaje a partir de comandos del usuario
    # ------------------------------------------------------------------

    def learn_from_command(self, comando: str, respuesta: str) -> None:
        self.profile.log_interaction(kind="command", text=comando, extra={"response": respuesta})
        lower = comando.lower()
        # Detectar ajuste de preferencias por comando.
        if "modo " in lower and ("voz" in lower or "texto" in lower or "escritura" in lower):
            if "voz y texto" in lower or "ambos" in lower:
                self.profile.set_interaction_mode("voice_and_text")
            elif "solo voz" in lower or "voz" in lower and "y texto" not in lower:
                if "texto" in lower and "voz" in lower:
                    self.profile.set_interaction_mode("voice_and_text")
                else:
                    self.profile.set_interaction_mode("voice_and_text")
            elif "solo texto" in lower or "escritura" in lower:
                self.profile.set_interaction_mode("text")
        if "estilo ejecutivo" in lower:
            self.profile.set_communication_style("ejecutivo")
        if "estilo informal" in lower or "informal" in lower:
            self.profile.set_communication_style("informal")
        if "tengo una reunión" in lower:
            self.profile.remember_todo({
                "text": comando,
                "done": False,
            })

    # ------------------------------------------------------------------
    # Resumen / sincronización con el store backend
    # ------------------------------------------------------------------

    def summary_for_store(self) -> Dict[str, Any]:
        base = self.profile.summary()
        return {
            "language": base.get("language"),
            "interaction_mode": base.get("interaction_mode"),
            "style": base.get("style"),
            "response_length": base.get("response_length"),
            "open_todos": base.get("open_todos"),
            "interactions": base.get("interactions"),
            "likely_focus": self.likely_current_focus(),
            "dominant_keywords": self.dominant_keywords(10),
        }

    def sync_to_store(self) -> None:
        from kitian import store as kitian_store
        payload: Dict[str, Any] = {}
        p = self.summary_for_store()
        if p.get("interaction_mode"):
            payload["interactionType"] = p["interaction_mode"]
        if p.get("style"):
            payload["responseStyle"] = p["style"]
        if p.get("response_length"):
            payload["responseLength"] = p["response_length"]
        if p.get("likely_focus"):
            payload["focusTopic"] = p["likely_focus"]
        if payload:
            try:
                kitian_store.merge({"preferences": payload})
            except Exception:
                pass
        self._synced = True

    def summary(self) -> Dict[str, Any]:
        base = self.profile.summary()
        base["dominant_keywords"] = self.dominant_keywords(10)
        base["likely_focus"] = self.likely_current_focus()
        return base
