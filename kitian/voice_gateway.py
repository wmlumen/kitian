"""Gateway ligero de voz para Kitian.

Endpoints:
- POST /api/voice/interact -> igual que antes, con fallback de audio
- POST /api/voice/push-to-talk -> graba 6s/ hasta silencio, transcribe, dispatch
- POST /api/voice/wakeword-toggle -> activa/desactiva wakeword
- GET  /api/voice/status -> estado de voz
- POST /api/voice/speak -> sintetiza texto (TTS)
"""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np

from kitian.store import kitian_store
from kitian.audio import load_whisper, transcribir_local, grabar, hablar
from kitian.voice_flow import process_voice
from kitian.wakeword import WakeWordBridge


_HOST = os.environ.get("KITIAN_VOICE_HOST", "0.0.0.0")
_PORT = int(os.environ.get("KITIAN_VOICE_PORT", "8082"))

# globals
_wakeword_bridge = None
_wakeword_thread = None
_wakeword_stop = threading.Event()
_wakeword_lock = threading.Lock()


def _ensure_wakeword() -> WakeWordBridge:
    global _wakeword_bridge
    if _wakeword_bridge is None:
        _wakeword_bridge = WakeWordBridge(words=["kitian"], threshold=0.5)
        try:
            _wakeword_bridge.init()
        except Exception:
            pass
    return _wakeword_bridge


def _set_voice_state(patch: dict) -> None:
    try:
        kitian_store.merge({"voice": patch})
    except Exception:
        pass


def _get_voice_state() -> dict:
    try:
        state = kitian_store.get()
        return dict(state.get("voice", {}))
    except Exception:
        return {}


def _do_audio_pipeline(timeout: float = 6.0) -> tuple[str | None, str | None]:
    """Record with vad/whisper, return (texto, via)."""
    try:
        if not load_whisper():
            return None, None
        audio = grabar(duracion=min(timeout, 8.0))
        if audio is None:
            return None, None
        # Use audio directly; caller can pre-VAD if needed.
        texto = transcribir_local(audio)
        if texto:
            return texto.strip(), "voice"
        return None, None
    except Exception:
        return None, None


def _handle_transcription(texto: str) -> str | None:
    if not texto:
        return None
    _set_voice_state({"listening": False, "wakewordDetected": False})
    try:
        respuesta = process_voice(texto)
    except Exception as e:
        respuesta = f"[Voice error] {e}"
    try:
        kitian_store.merge({
            "inputs": {
                "lastCommand": texto,
                "lastResponse": respuesta,
                "listening": False,
                "voiceMode": "PUNCTUAL",
            }
        })
    except Exception:
        pass
    return respuesta


def _wakeword_loop():
    bridge = _ensure_wakeword()
    # Optional VAD via sounddevice; skip gracefully if not available.
    vad_ready = False
    try:
        from kitian.vad import _ensure_stream, _stop_stream, _drain_frame
        vad_ready = True
    except Exception:
        vad_ready = False

    if vad_ready:
        try:
            if _ensure_stream():
                pass
            else:
                vad_ready = False
        except Exception:
            vad_ready = False

    sample_rate = 16000
    frame_ms = 32
    frame_samples = int(sample_rate * frame_ms / 1000)

    buf = []
    speaking = False
    speak_start = 0.0

    while not _wakeword_stop.is_set():
        try:
            if vad_ready:
                try:
                    frame = _drain_frame(None)  # uses globals
                except Exception:
                    frame = None
                if frame is None:
                    time.sleep(0.05)
                    continue
            else:
                # fallback: short numpy zeros to keep loop alive without crashing
                time.sleep(0.1)
                continue

            scores = bridge.score(frame)
            activated = any((v or 0) > 0.5 for v in scores.values()) if scores else False

            if activated and not speaking:
                speaking = True
                speak_start = time.time()
                buf = []
                _set_voice_state({"listening": True, "wakewordDetected": True, "wakewordActive": True})
                try:
                    hablar("¿Sí?", blocking=False)
                except Exception:
                    pass
                continue

            if speaking:
                buf.append(frame)
                if time.time() - speak_start > 6.0:
                    speaking = False
                    buf_np = np.concatenate(buf) if buf else np.zeros((1,), dtype=np.int16)
                    texto, _ = _do_audio_pipeline(timeout=0.5)
                    if texto:
                        respuesta = _handle_transcription(texto)
                        if respuesta:
                            try:
                                hablar(respuesta, blocking=False)
                            except Exception:
                                pass
                    _set_voice_state({"wakewordActive": False})
                    continue
        except Exception:
            time.sleep(0.1)

    if vad_ready:
        try:
            _stop_stream()
        except Exception:
            pass
    _set_voice_state({"listening": False, "wakewordActive": False, "wakewordDetected": False})


class VoiceHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # keep quiet for non-errors
        if args and str(args[1]).startswith(("4", "5")):
            print(f"[VOICE] {args[0]} {args[1]}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status, data):
        try:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, OSError):
            pass

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8", errors="replace") or "{}")
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/voice/status":
            return self._send(200, _get_voice_state())
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/voice/interact":
            return self._handle_interact()
        if self.path == "/api/voice/push-to-talk":
            return self._handle_ptt()
        if self.path == "/api/voice/wakeword-toggle":
            return self._handle_wakeword_toggle()
        if self.path == "/api/voice/speak":
            return self._handle_speak()
        return self._send(404, {"error": "not found"})

    def _handle_interact(self):
        body = self._read_body()
        texto = (body.get("texto") or "").strip()
        transcription = texto or None
        via = "text"
        if not transcription:
            try:
                t, v = _do_audio_pipeline(timeout=6.0)
                transcription = t
                via = v or via
            except Exception as e:
                return self._send(500, {"ok": False, "error": f"audio pipeline error: {e}"})
        if not transcription:
            return self._send(400, {"error": "audio no disponible y texto vacío"})
        respuesta = _handle_transcription(transcription)
        _set_voice_state({"listening": False})
        return self._send(200, {"ok": True, "texto": transcription, "respuesta": respuesta, "via": via})

    def _handle_ptt(self):
        _set_voice_state({"pttActive": True, "listening": True})
        try:
            if _get_voice_state().get("wakewordActive"):
                try:
                    _handle_wakeword_toggle()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            texto, via = _do_audio_pipeline(timeout=6.0)
        except Exception:
            texto, via = None, None
        _set_voice_state({"pttActive": False, "listening": False, "voiceMode": "PUNCTUAL"})
        if not texto:
            return self._send(400, {"error": "no audio"})
        respuesta = _handle_transcription(texto)
        return self._send(200, {"ok": True, "texto": texto, "respuesta": respuesta, "via": via or "voice"})

    def _handle_wakeword_toggle(self):
        global _wakeword_thread
        with _wakeword_lock:
            if _wakeword_thread and _wakeword_thread.is_alive():
                _wakeword_stop.set()
                try:
                    _wakeword_thread.join(timeout=2)
                except Exception:
                    pass
                _wakeword_thread = None
                _set_voice_state({"wakewordActive": False, "listening": False})
                return self._send(200, {"ok": True, "active": False})
            else:
                _wakeword_stop.clear()
                t = threading.Thread(target=_wakeword_loop, daemon=True, name="wakeword")
                t.start()
                _wakeword_thread = t
                _set_voice_state({"wakewordActive": True, "voiceMode": "WAKE"})
                return self._send(200, {"ok": True, "active": True})

    def _handle_speak(self):
        body = self._read_body()
        texto = (body.get("texto") or "").strip()
        if not texto:
            return self._send(400, {"error": "texto vacío"})
        try:
            hablar(texto, blocking=False)
        except Exception as e:
            return self._send(500, {"ok": False, "error": str(e)})
        return self._send(200, {"ok": True})


def start_background():
    if os.environ.get("KITIAN_VOICE_DISABLED") == "1":
        return
    server = HTTPServer((_HOST, _PORT), VoiceHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="voice-http")
    t.start()
    print(f"[VoiceGateway] http://{_HOST}:{_PORT}/api/voice/interact")
    return server


if __name__ == "__main__":
    server = HTTPServer((_HOST, _PORT), VoiceHandler)
    print(f"[VoiceGateway] Running http://{_HOST}:{_PORT}/api/voice/interact")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
