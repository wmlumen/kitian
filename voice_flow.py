"""Modulo core de voz de Kitian."""  
import time  
from typing import Dict, Any, Optional  

class VoiceFlow:  
    """Procesamiento vocal unificado con deteccion de intenciones y gestion de contexto."""  
      
    def __init__(self, tts_enabled: bool = True, default_response_type: str = "balanced"):  
        self.tts_enabled = tts_enabled  
        self.response_type = default_response_type  
        self.conversation_history: list = []  
        self.user_profile: Dict[str, Any] = {}  
          
        # Estados vocales  
        self.states = {  
            "idle": {"text": "En espera", "icon": "○", "color": "gray"},  
            "listening": {"text": "Escuchando...", "icon": "◉", "color": "cyan"},  
            "processing": {"text": "Procesando", "icon": "◈", "color": "amber"},  
            "speaking": {"text": "Respondiendo", "icon": "▶", "color": "green"}  
        }  
        self.current_state = "idle"  
        self.last_error: Optional[str] = None  
  
    def set_state(self, state: str):  
        """Cambia el estado vocal y notifica a los clientes."""  
        if state in self.states:  
            self.current_state = state  
            return self.states[state]  
        return self.states["idle"]  
  
    def get_state_info(self) -> Dict[str, Any]:  
        """Devuelve el estado actual para APIs."""  
        base = self.states.get(self.current_state, self.states["idle"]).copy()  
        base["state"] = self.current_state  
        base["tts_enabled"] = self.tts_enabled  
        base["last_error"] = self.last_error  
        return base  
  
    def understand_intent(self, text: str, context: str = "") -> Dict[str, Any]:  
        """Clasificacion de intenciones con heuristica mejorada."""  
        cleaned = text.lower().strip()  
        words = cleaned.split()  
          
        # Saludos y despedidas  
        if any(w in words for w in ["hola", "hey", "ey", "buenas", "qué tal", "como estas"]):  
            return {"intent": "saludo", "confidence": 1.0, "response_type": "normal"}  
          
        # Confirmaciones  
        if any(w in words for w in ["gracias", "perfecto", "listo", "ok", "vale", "genial"]):  
            return {"intent": "confirmacion", "confidence": 1.0, "response_type": "short"}  
          
        # Despedidas  
        if any(w in words for w in ["adios", "chao", "hasta luego", "nos vemos"]):  
            return {"intent": "despedida", "confidence": 1.0, "response_type": "short"}  
          
        # Peticiones de accion  
        if any(w in words for w in ["haz", "ejecuta", "genera", "crea", "procesa", "envia"]):  
            return {"intent": "accion", "confidence": 0.85, "response_type": "detailed"}  
          
        # Peticiones de informacion  
        if any(w in words for w in ["que", "quien", "cuando", "donde", "como", "por que", "cual"]):  
            return {"intent": "pregunta", "confidence": 0.8, "response_type": "balanced"}  
          
        # Comandos directos  
        if text.startswith("/") or text.startswith("!"):  
            return {"intent": "comando", "confidence": 0.9, "response_type": "short"}  
          
        # Peticiones de explicacion  
        if any(w in words for w in ["explica", "detalla", "amplia", "mas largo"]):  
            return {"intent": "explicacion", "confidence": 0.75, "response_type": "detailed"}  
          
        # Peticiones de resumen  
        if any(w in words for w in ["resumen", "resume", "conciso", "corto"]):  
            return {"intent": "resumen", "confidence": 0.75, "response_type": "short"}  
          
        # Default  
        return {"intent": "dialogo", "confidence": 0.4, "response_type": "balanced"}  
  
    def process_interaction(self, user_text: str, context: str = "", extra: Dict[str, Any] = None) -> Dict[str, Any]:  
        """Flujo completo de procesamiento vocal."""  
        extra = extra or {}  
        self.set_state("processing")  
          
        try:  
            # 1) Entender intencion  
            intent_data = self.understand_intent(user_text, context)  
              
            # 2) Generar respuesta coherente (no random, basada en contexto real)  
            response_text = self._build_response(intent_data, user_text, context, extra)  
              
            # 3) Decidir si debe hablarse  
            should_speak = self.tts_enabled and intent_data.get("response_type") != "error"  
              
            # 4) Registrar en historial  
            self.conversation_history.append({  
                "role": "user",  
                "text": user_text,  
                "timestamp": time.time()  
            })  
            self.conversation_history.append({  
                "role": "assistant",  
                "text": response_text,  
                "intent": intent_data["intent"],  
                "timestamp": time.time(),  
                "tts": should_speak  
            })  
              
            # 5) Limitar historial  
            if len(self.conversation_history) > 200:  
                self.conversation_history = self.conversation_history[-100:]  
              
            # 6) Determinar longitud para TTS  
            if should_speak:  
                if intent_data["response_type"] == "short":  
                    response_text = self._shorten_for_speech(response_text)  
                elif intent_data["response_type"] == "detailed":  
                    response_text = self._expand_for_speech(response_text, context)  
              
            return {  
                "ok": True,  
                "text": response_text,  
                "intent": intent_data["intent"],  
                "intent_confidence": intent_data.get("confidence", 0.5),  
                "tts": should_speak,  
                "response_type": intent_data.get("response_type", "balanced"),  
                "state": self.current_state,  
                "history_length": len(self.conversation_history)  
            }  
              
        except Exception as e:  
            self.last_error = str(e)  
            self.set_state("idle")  
            return {  
                "ok": False,  
                "error": str(e),  
                "tts": False,  
                "state": self.current_state  
            }  
        finally:  
            if self.current_state != "idle":  
                self.set_state("idle")  
  
    def _build_response(self, intent: Dict[str, Any], user_text: str, context: str, extra: Dict[str, Any]) -> str:  
        """Genera respuestas coherentes sin contenido aleatorio."""  
        intent_type = intent.get("intent", "dialogo")  
        response_type = intent.get("response_type", "balanced")  
          
        # Limitar contexto  
        ctx = context.strip()[:800] if context else ""  
        user = user_text.strip()[:120]  
          
        if intent_type == "saludo":  
            return f"Hola, soy Kitian. {ctx[:100] if ctx else 'En que puedo ayudarte?'}"  
              
        elif intent_type == "confirmacion":  
            return "Perfecto. Avísame si necesitas algo más."  
              
        elif intent_type == "despedida":  
            return "Hasta luego. Aquí estaré cuando me necesites."  
              
        elif intent_type == "accion":  
            if ctx:  
                return f"Procedo con: {ctx[:200]}"  
            return "Entendido, ejecutando."  
              
        elif intent_type == "pregunta":  
            if ctx:  
                return ctx[:400]  
            return "No tengo suficiente contexto para responder eso ahora mismo."  
              
        elif intent_type == "explicacion":  
            if ctx:  
                return f"{ctx[:500]} ¿Necesitas que profundice en algun punto?"  
            return "Todos los detalles listos para cuando tengas contexto disponible."  
              
        elif intent_type == "resumen":  
            if ctx:  
                # Versión forzadamente corta  
                short = ctx.replace('\n', ' ').strip()[:120]  
                return short if short else ctx[:120]  
            return "Resumen disponible cuando llegue el contexto."  
              
        elif intent_type == "comando":  
            return f"Comando recibido: {user}. Ejecutando rutina."  
              
        # dialogo general  
        if ctx:  
            return ctx[:500]  
        return f"Recibi: {user}. ¿Necesitas algo concreto?"  
  
    def _shorten_for_speech(self, text: str, max_words: int = 25) -> str:  
        """Reduce texto para TTS fluido."""  
        words = text.split()  
        if len(words) <= max_words:  
            return text  
        return " ".join(words[:max_words]) + "..."