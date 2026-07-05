# Kitian — Contexto del Proyecto

## Identidad
- **Nombre:** Kitian
- **Tipo:** Asistente personal de escritorio con voz y panel web / widget HUD
- **Inspiración:** JARVIS (Iron Man)
- **Estado:** post-auditoría · activo
- **Regla de ejecución:** WSL solo para desarrollo. El HUD Tkinter y el audio nativo se ejecutan desde Windows.

## Stack técnico confirmado
- **Lenguaje:** Python 3.14
- **UI Web:** `nebula_web.html` servido por HTTP standalone
- **UI HUD:** `kitian_hud.py` (Tkinter Canvas), solo ejecutable desde Windows
- **Audio entrada:** sounddevice 16000 Hz mono int16 + Faster-Whisper `small` + Silero VAD
- **Audio salida:** pyttsx3 (SAPI5) con lock; Piper TTS documentado como próximo
- **Motor IA:** OpenAI-compatible (LM Studio local, Gemini, OpenAI, Groq, Nous)
- **Logs:** `kitian.log`
- **Estado backend SSOT:** `kitian/store.py` — `kitian_store`; `kitian/state.py` es fachada legacy

## Realidad del entorno
- `C:\Temp\kitian\` es la carpeta real de ejecución en Windows.
- WSL no puede renderizar HUD Tkinter ni capturar micrófono nativo; usar `activar_kitian.bat` o `powershell.exe` desde Windows.
- Acceso directo del escritorio: `C:\Users\HP 250 G10\Desktop\Kitian.lnk`
- Puertos principales: HTTP `8080`, Voz `8082`
- En desarrollo local es preferible forzar recarga del navegador porque el HTML se sirve con `Cache-Control: no-store`.

## Arquitectura

```
Windows (ejecución real)
├─ activar_kitian.bat -> lanza kitian_http_standalone_real.py
├─ kitian_http_standalone_real.py :8080
│   ├─ GET /, /nebula -> nebula_web.html
│   ├─ GET /api/system, /api/health, /api/status
│   ├─ GET/POST /api/hermes/*
│   ├─ POST /api/command -> dispatcher_local -> fallback Hermes
│   └─ proxy /api/voice/* -> localhost:8082
└─ kitian/voice_gateway.py :8082
    ├─ POST /api/voice/interact
    ├─ POST /api/voice/push-to-talk
    ├─ POST /api/voice/wakeword-toggle
    ├─ POST /api/voice/speak
    └─ GET /api/voice/status

WSL (edición/scripting únicamente)
└─ /mnt/c/Temp/kitian/ -> mismo repo
```

## Flujo de comando

1. Usuario escribe en `nebula_web.html` o habla por `/api/voice/interact`.
2. Backend prueba dispatcher local de Kitian.
3. Si no hay match, hace fallback a Hermes por subprocess.
4. Respuesta se muestra en UI; si voz activa, se reproduce con `hablar()`.

## Endpoints mínimos que deben mantenerse
- `GET /api/system`
- `GET /api/health`
- `GET /api/status`
- `GET /api/hermes/status`
- `POST /api/command`
- `POST /api/hermes/chat`
- `POST /api/voice/interact`
- `POST /api/voice/push-to-talk`
- `POST /api/voice/speak`
- `POST /api/voice/wakeword-toggle`
- `GET /api/voice/status`

## Dependencias Python
```
openai, psutil, faster-whisper, silero-vad, onnxruntime, numpy,
pyttsx3, sounddevice, keyboard, python-dotenv, tkinter (stdlib)
```

## Reglas del proyecto

1. Nunca subir a GitHub sin autorización explícita.
2. `.env`, `kitian.log`, `kitian_config.json` en `.gitignore`.
3. No modificar `GITHUT/` sin permiso.
4. Loggear errores relevantes; no romper el launcher Windows.
5. Toda ruta nueva en backend debe nacer en `store.py` cuando toque estado compartido.
6. Probar cambios desde Windows. Si se edita `nebula_web.html`, forzar recarga del navegador.

## Hacer / No hacer

### Hacer
- Editar desde WSL y ejecutar desde Windows.
- Actualizar `store.py` antes de inventar otro estado global.
- Verificar `/api/health` y `/api/voice/status` tras cada cambio de backend.
- Capturar errores de audio en `kitian/audio.py` sin romper el loop principal.

### No hacer
- No romper `/api/command` ni `/api/voice/interact` sin verificar JSON de respuesta.
- No mover proxies `/api/voice/*` a rutas distintas sin actualizar voice_gateway.
- No forzar `localhost` cuando el diagnóstico muestre binding en `0.0.0.0:8080`; verificar IP real accesible desde Windows.
- No agregar health checks automáticos en UI salvo petición expresa.
- No subir backups ni artefactos de edición a menos que se indique.

## Pendiente de corregir
- [ ] Audio en Windows: captura nativa sin WSL; validar `sounddevice` y pipeline `/api/voice/interact` desde `C:\Python314\python.exe`.
- [ ] HUD Tkinter: confirmar visually desde Windows; no esperar render en WSL.
- [ ] Smoke tests backend en Windows: `/api/health`, `/api/voice/status`, `/api/voice/wakeword-toggle`, `/api/voice/push-to-talk`.
- [ ] Hermes bridge: confirmar salida limpia desde `/api/hermes/chat` y `/api/command`.
- [ ] Launchers: validar `activar_kitian.bat` y `Kitian.lnk` con icono `reddot.ico` en escritorio real.
- [ ] Skills: cerrar actualización pendiente de `kitian`/`local-assistant` con reglas firmes y checklist.

## Próximos pasos sugeridos
1. Ejecutar diagnóstico completo desde Windows antes de modificar audio/UI.
2. Mantener `kitian_hud.py` como opción válida, sin reemplazar por defecto el panel web.
3. Si Hermes responde por `/api/hermes/chat`, usar ese canal como fallback oficial documentado.
