# Kitian — Listado de pendientes (post-referencia D.A.W.N./listado JARVIS)

## Prioridad Alta (bloqueantes para UX)
1. Silero VAD — detección de inicio/fin de voz; reducir silencios y falsas activaciones.
2. openWakeWord — activación por palabra clave “Kitian” en escucha continua.
3. Faster-Whisper — migrar STT a CTranslate2; menor latencia y consumo.
4. Interrupción de Piper — detener TTS cuando el usuario empieza a hablar.

## Prioridad Media (mejora funcional)
5. Memoria persistente avanzada — resúmenes de sesión y proveedor abstracto (SQLite ahora, Mem0 opcional después).
6. OmnIParser / ShowUI — lectura de pantalla estructurada (después de estabilizar voz).
7. Navigator–Localizer–Validator — control visual de escritorio (módulos independientes).
8. MCP bridge — exponer herramientas de Kitian a Hermes/otros agentes.

## Prioridad Baja (mejora de arquitectura)
9. Tests unitarios mínimos — core, audio, dispatcher.
10. CI básica — lint/py_compile automático.
11. Documentación agente-usable — SKILL.md vivo y ejemplos.
12. Empaquetado/SDK opcional — si se apunta a distribuir.

Siguiente paso sugerido: 1 y 2 del listado (Silero VAD + openWakeWord).
