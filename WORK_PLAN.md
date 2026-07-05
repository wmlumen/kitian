# Kitian — Plan de Trabajo Integral v2.0

> Basado en análisis de 810+ proyectos JARVIS en GitHub + gap analysis
> Estado: v0.3-dev (Piper TTS, APIManager, HUD, 45+ comandos)
> Meta: v1.0 (80%+ del camino a JARVIS)

---

## Fase 0: Cimientos (Ya completado)

| # | Feature | Archivo | Estado |
|---|---------|---------|--------|
| - | HUD Tkinter Canvas con anillos, radar, partículas | `kitian_hud.py` | ✅ |
| - | Wake word "Kitian" + 8 variaciones | `kitian_full.py` | ✅ |
| - | Piper TTS neural (carlfm) con fallback pyttsx3 | `kitian_tts.py` | ✅ |
| - | APIManager con 3 APIs de clima + caché | `kitian_full.py` | ✅ |
| - | Dispatcher local 45+ comandos | `kitian_full.py` | ✅ |
| - | Multi-backend LLM (LM Studio, OpenAI, Gemini, Groq) | `kitian_full.py` | ✅ |
| - | Captura de pantalla + control de volumen | `kitian_full.py` | ✅ |
| - | Memoria conversación (últimas 20) | `kitian_full.py` | ✅ |
| - | Logs, .env, hotkey Ctrl+Space | `kitian_full.py` | ✅ |

---

## Fase 1: Voz y Percepción (Semanas 1-2)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 1 | **Whisper STT local** — reemplazar Google STT | `kitian_full.py`, nuevo `kitian_stt.py` | `faster-whisper`, modelo `tiny` | 3 días |
| 2 | **VAD (Voice Activity Detection)** — detectar inicio/fin de habla | `kitian_full.py` | `silero-vad` o `webrtcvad` | 2 días |
| 3 | **Wake Word dedicado** — Porcupine/OpenWakeWord, modelo "Kitian" | `kitian_full.py` | `pvporcupine` | 2 días |
| 4 | **Streaming TTS** — hablar palabra por palabra mientras genera | `kitian_full.py`, `kitian_tts.py` | Piper streaming API | 2 días |
| 5 | **Interrupción full-duplex** — poder hablar mientras Kitian responde | `kitian_full.py` | VAD + buffer de audio | 3 días |

**Entregable Fase 1:** Kitian funciona 100% offline, responde en <500ms, te puede interrumpir.

---

## Fase 2: Memoria y Conocimiento (Semanas 3-4)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 6 | **Memoria persistente SQLite** — conversaciones, preferencias, comandos | `kitian_full.py`, nuevo `kitian_db.py` | `sqlite3` (stdlib) | 2 días |
| 7 | **Red de Conocimiento integrada** — comandos de voz para modos | `kitian_full.py`, `arquitecto_conocimiento.py` | ya existente | 2 días |
| 8 | **RAG con ChromaDB** — indexar documentos, respuestas contextuales | nuevo `kitian_rag.py` | `chromadb`, `sentence-transformers` | 3 días |
| 9 | **Perfil de usuario** — nombre, ciudad default, preferencias | `kitian_full.py`, `kitian_db.py` | SQLite | 1 día |
| 10 | **Recordatorios y alarmas** — "recuérdame X a las Y" | `kitian_full.py` | `schedule` o threading | 1 día |
| 11 | **Traducción** — "tradúceme esto al inglés" | `kitian_full.py` | LLM local o API | 1 día |

**Entregable Fase 2:** Kitian te conoce, recuerda, y responde sobre tus documentos.

---

## Fase 3: Control Total del Escritorio (Semanas 5-6)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 12 | **PyAutoGUI completo** — mouse, teclado, clicks, arrastres, escribir | `kitian_full.py` | `pyautogui` | 2 días |
| 13 | **Control de ventanas** — listar, mover, redimensionar, minimizar | `kitian_full.py` | `pygetwindow` | 1 día |
| 14 | **Notificaciones proactivas** — alertas de sistema, clima, batería | `kitian_full.py` | `plyer` o `win10toast` | 1 día |
| 15 | **Email y WhatsApp** — enviar mensajes por voz | nuevo `kitian_messaging.py` | `smtplib`, `pywhatkit` | 2 días |
| 16 | **Descarga de contenido** — YouTube, audio | `kitian_full.py` | `yt-dlp` | 1 día |
| 17 | **Modo desarrollador** — ejecutar código, git, terminal | `kitian_full.py` | `subprocess`, `gitpython` | 2 días |

**Entregable Fase 3:** Kitian controla tu PC como si fueran tus manos.

---

## Fase 4: Arquitectura y Escalabilidad (Semanas 7-8)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 18 | **Sistema de plugins** — carpeta `plugins/`, carga dinámica, manifiestos JSON | `kitian_full.py`, `plugins/` | stdlib | 4 días |
| 19 | **API REST (FastAPI)** — control remoto, dashboard web | nuevo `kitian_api.py` | `fastapi`, `uvicorn` | 3 días |
| 20 | **Multi-agente** — agentes especializados (chat, research, monitor) | `kitian_full.py`, `plugins/` | basado en plugins | 3 días |

**Entregable Fase 4:** Kitian es modular, extensible, y controlable remotamente.

---

## Fase 5: Visión y Multimedia (Semanas 9-10)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 21 | **OCR** — leer texto de imágenes, capturas, PDFs | `kitian_full.py` | `pytesseract`, `PIL` | 2 días |
| 22 | **Visión por computadora** — webcam, detección objetos | nuevo `kitian_vision.py` | `opencv-python` | 3 días |
| 23 | **Detección facial** — reconocer usuario autorizado | `kitian_vision.py` | `deepface` | 2 días |
| 24 | **Dashboard web 3D** — Three.js, complemento al HUD | `dashboard/` (nuevo) | Node.js, Three.js | 5 días |

---

## Fase 6: Conectividad (Semanas 11-12)

| # | Mejora | Archivos | Dependencias | Tiempo |
|---|--------|----------|-------------|--------|
| 25 | **Bot de Telegram** — comandos por mensaje | `kitian_full.py` | `python-telegram-bot` | 2 días |
| 26 | **Calendario Google** — sincronizar eventos | `kitian_full.py` | `google-api-python-client` | 2 días |
| 27 | **Smart home / IoT** — luces, dispositivos | `plugins/smarthome/` | MQTT, HTTP | 3 días |
| 28 | **Instalador Windows** — .exe con PyInstaller | `setup/` | `pyinstaller` | 1 día |

---

## Cronograma Visual

```
SEMANA:  1  2  3  4  5  6  7  8  9 10 11 12
         ████████████████████████████████████
Fase 1:  ████████                            Voz/Percepción
Fase 2:          ████████                    Memoria/Conocimiento
Fase 3:                  ████████            Control Desktop
Fase 4:                          ████████    Arquitectura/Plugins
Fase 5:                                  ████ Visión
Fase 6:                                      ██ Conectividad
```

## Métricas de Progreso

| Métrica | Ahora | F1 | F2 | F3 | F4 | F5 | F6 |
|---------|-------|----|----|----|----|----|-----|
| Voz | 40% | 85% | 85% | 85% | 85% | 85% | 85% |
| Memoria | 25% | 25% | 70% | 70% | 70% | 70% | 75% |
| Desktop | 20% | 20% | 20% | 75% | 75% | 75% | 75% |
| Plugins | 5% | 5% | 5% | 5% | 70% | 70% | 80% |
| Visión | 0% | 0% | 0% | 0% | 0% | 60% | 60% |
| Conectividad | 15% | 15% | 15% | 15% | 30% | 30% | 70% |
| **TOTAL** | **28%** | **42%** | **52%** | **62%** | **72%** | **77%** | **82%** |

## Dependencias por Fase

```
Fase 0 (OK)
  └─► Fase 1 (Voz) ──► Fase 2 (Memoria) ──► Fase 3 (Desktop)
                           │                       │
                           └───────► Fase 4 (Plugins) ──► Fase 6 (Conectividad)
                                                              │
                           Fase 5 (Visión) ◄──────────────────┘
```

## Archivos del Proyecto al Final

```
C:\Temp\kitian\
├── kitian_full.py              ← Motor principal (~1500 líneas)
├── kitian_hud.py               ← HUD Tkinter Canvas
├── kitian_tts.py               ← Piper TTS neural
├── kitian_stt.py               ← Whisper STT local (Fase 1)
├── kitian_db.py                ← SQLite persistencia (Fase 2)
├── kitian_rag.py               ← ChromaDB + embeddings (Fase 2)
├── kitian_messaging.py         ← Email + WhatsApp (Fase 3)
├── kitian_vision.py            ← OCR + cámara (Fase 5)
├── kitian_api.py               ← FastAPI server (Fase 4)
├── arquitecto_conocimiento.py  ← Red de conocimiento
├── escaneo_inicial.py          ← Escáner documentos
├── plugins/                    ← Sistema modular (Fase 4)
│   ├── __init__.py
│   ├── datos/                  ← Clima, noticias, búsqueda
│   ├── escritorio/             ← PyAutoGUI, ventanas
│   ├── smarthome/              ← IoT (Fase 6)
│   └── vision/                 ← OCR, cámara (Fase 5)
├── piper_models/               ← Voces Piper
├── dashboard/                  ← Web 3D (Fase 5)
├── .env
├── .gitignore
├── kitian_config.json
├── WORK_PLAN.md
├── PROJECT.md
└── README.md
```

---

## Próximo paso inmediato

**Fase 1, Item 1: Whisper STT local**

```bash
pip install faster-whisper
python -c "from faster_whisper import WhisperModel; m = WhisperModel('tiny'); print('Whisper listo')"
```

Archivos a tocar: `kitian_full.py` (reemplazar Google STT), nuevo `kitian_stt.py`.

¿Arranco con esto?
