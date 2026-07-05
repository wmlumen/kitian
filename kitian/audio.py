import logging
import os
import threading
import time
import queue
import collections
from typing import Optional

import numpy as np

log = logging.getLogger("kitian")

# --- Optional imports ---
try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    sd = None
    HAS_SD = False

try:
    import pyaudio
    HAS_PORTAUDIO = True
except Exception:
    pyaudio = None
    HAS_PORTAUDIO = False

try:
    import speech_recognition as sr
    HAS_SR = True
except Exception:
    sr = None
    HAS_SR = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except Exception:
    pyttsx3 = None
    HAS_PYTTSX3 = False

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    WhisperModel = None
    HAS_WHISPER = False

try:
    import torch
except ImportError:
    torch = None

try:
    import onnxruntime
except ImportError:
    onnxruntime = None

# --- Globals ---
_whisper = None
_pyttsx3_lock = threading.Lock()
_silero_model = None
_silero_get_speech_ts = None
HAS_SILERO = torch is not None

VAD_THRESHOLD = 0.5
VAD_SAMPLE_RATE = 16000
VAD_WINDOW_MS = 96
VAD_SPEECH_PAD_MS = 120
VAD_MIN_SPEECH_MS = 280
VAD_MIN_SILENCE_MS = 360


def _load_silero_utils():
    model = None
    get_speech_ts = None
    try:
        if onnxruntime is not None:
            try:
                from silero_vad import load_silero_vad, get_speech_timestamps
                model = load_silero_vad(
                    onnx_optimization_level=onnxruntime.OptimizationLevel.ORT_ENABLE_ALL
                )
                get_speech_ts = get_speech_timestamps
            except Exception:
                pass
    except Exception:
        pass
    if model is None and torch is not None:
        try:
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            get_speech_ts = utils[0] if isinstance(utils, (list, tuple)) else getattr(utils, "get_speech_timestamps", None)
        except Exception:
            pass
    return model, get_speech_ts


def _ensure_silero():
    global _silero_model, _silero_get_speech_ts
    if _silero_model is not None and _silero_get_speech_ts is not None:
        return True
    if not HAS_SILERO:
        return False
    _silero_model, _silero_get_speech_ts = _load_silero_utils()
    return _silero_model is not None and _silero_get_speech_ts is not None


def audio_to_float32(audio_np):
    if audio_np.dtype == np.int16:
        return audio_np.astype(np.float32) / 32768.0
    return audio_np.astype(np.float32)


def vad_segmented(audio, sample_rate=16000):
    if audio.size == 0:
        return None
    if not _ensure_silero():
        return audio
    wav = audio_to_float32(audio.reshape(-1))
    try:
        segments = _silero_get_speech_ts(wav, _silero_model, sampling_rate=sample_rate, threshold=VAD_THRESHOLD)
    except Exception:
        return audio
    if not segments:
        return None
    min_samples = int(VAD_MIN_SPEECH_MS / 1000.0 * sample_rate)
    valid = [s for s in segments if (s["end"] - s["start"]) >= min_samples]
    if not valid:
        return audio
    start = valid[0]["start"]
    end = valid[-1]["end"]
    pad = int(VAD_SPEECH_PAD_MS / 1000.0 * sample_rate)
    start = max(0, start - pad)
    end = min(wav.shape[0], end + pad)
    cut = wav[start:end]
    return (cut * 32768.0).astype(np.int16)


def _segments_from_ts(audio, ts, sample_rate):
    if audio.size == 0 or not ts:
        return audio
    start = max(s["start"] for s in ts)
    end = min(s["end"] for s in ts)
    pad = int(VAD_SPEECH_PAD_MS / 1000.0 * sample_rate)
    start = max(0, start - pad)
    end = min(audio.shape[0], end + pad)
    return audio[start:end]


def load_whisper():
    global _whisper
    if not HAS_WHISPER:
        return False
    if _whisper is not None:
        return True
    try:
        log.info("Cargando Faster-Whisper 'small'...")
        _whisper = WhisperModel("small", device="cpu", compute_type="int8")
        log.info("Faster-Whisper 'small' listo")
        return True
    except Exception as e:
        log.error("Faster-Whisper error: %s", e)
        return False


def transcribir_local(audio_numpy):
    if not HAS_WHISPER or _whisper is None:
        return None
    try:
        audio = audio_to_float32(audio_numpy)
        segments, info = _whisper.transcribe(
            audio,
            beam_size=5,
            language="es",
            vad_filter=True,
        )
        texto = " ".join(seg.text for seg in segments).strip()
        texto = " ".join(texto.split())
        log.info("Idioma detectado: %s", getattr(info, "language", "es"))
        return texto or None
    except Exception:
        return None


def grabar(duracion=6.0):
    if HAS_SD:
        data = sd.rec(
            int(duracion * VAD_SAMPLE_RATE),
            samplerate=VAD_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocking=True,
        )
        return data.flatten()
    if HAS_SR:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            log.info("Escuchando por microfono...")
            audio = r.listen(source, timeout=min(duracion, 8), phrase_time_limit=duracion)
            return np.frombuffer(audio.frame_data, dtype=np.int16)
    raise RuntimeError("No hay backend de audio disponible")


class VADStream:
    def __init__(self, vad_ready_cb=None, text_cb=None, audio_engine=None):
        self.vad_ready_cb = vad_ready_cb
        self.text_cb = text_cb
        self.audio_engine = audio_engine
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._running = False
        self._thread = None
        self._state = "inactive"
        self._output_queue = ""

    @property
    def state(self):
        return self._state

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="vad-stream", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._state = "inactive"

    def interrupt(self):
        if self.audio_engine and getattr(self.audio_engine, "engine", None):
            try:
                self.audio_engine.engine.stop()
            except Exception:
                pass

    def _update_output_queue(self, extra):
        self._output_queue = (self._output_queue + " " + extra).strip()

    def _loop(self):
        if not self._safety_check():
            self._state = "inactive"
            return
        self._state = "idle"
        if self.vad_ready_cb:
            try:
                self.vad_ready_cb("vad_ready", True)
            except Exception:
                pass
        frames_per_block = int(VAD_SAMPLE_RATE * VAD_WINDOW_MS / 1000)
        buffer = collections.deque(maxlen=frames_per_block * 8)
        status = "silence"
        speech_start = None
        speech_audio = []
        while not self._stop.is_set():
            block = sd.rec(frames_per_block, samplerate=VAD_SAMPLE_RATE, channels=1, dtype="int16", blocking=True).flatten()
            if not block.size:
                continue
            buffer.extend(block.tolist())
            arr = np.asarray(buffer, dtype=np.int16)
            wav = audio_to_float32(arr.reshape(-1))
            is_speech = False
            try:
                is_speech = bool(_silero_get_speech_ts(wav, _silero_model, sampling_rate=VAD_SAMPLE_RATE, threshold=VAD_THRESHOLD))
            except Exception:
                is_speech = False
            if status == "silence":
                if is_speech:
                    speech_start = time.time()
                    speech_audio = [arr]
                    status = "speech"
                    self._state = "speech"
                    self._update_output_queue("")
            else:
                speech_audio.append(arr)
                if not is_speech:
                    silence_elapsed = (time.time() - speech_start) if speech_start else 0
                    if silence_elapsed * 1000 >= VAD_MIN_SILENCE_MS:
                        full = np.concatenate(speech_audio) if speech_audio else arr
                        seg = vad_segmented(full, VAD_SAMPLE_RATE)
                        if seg is None:
                            seg = full
                        texto = transcribir_local(seg)
                        if not texto and HAS_SR:
                            try:
                                r = sr.Recognizer()
                                audio_sr = sr.AudioData(seg.tobytes(), VAD_SAMPLE_RATE, 2)
                                texto = r.recognize_google(audio_sr, language="es-ES")
                            except Exception:
                                texto = None
                        if texto:
                            self._update_output_queue(texto)
                            if self.text_cb:
                                try:
                                    self.text_cb("vad_text", texto)
                                except Exception:
                                    pass
                        status = "silence"
                        speech_audio = []
                        self._state = "idle"
        self._state = "inactive"

    def _safety_check(self):
        if not HAS_SD:
            log.warning("Falta sounddevice para VADStream")
            return False
        return _ensure_silero()


# ---------------------------------------------------------------------------
# TTS — Worker dedicado para pyttsx3 (soluciona CoInitialize en Windows)
# pyttsx3 en Windows necesita que el engine viva en el mismo hilo COM.
# Usamos un único hilo daemon con su propio engine y una cola de mensajes.
# ---------------------------------------------------------------------------

_tts_queue: queue.Queue = queue.Queue()
_tts_worker_started = False
_tts_worker_lock = threading.Lock()
_tts_engine_ref = [None]   # mutable ref accesible desde fuera del hilo


def _tts_worker_thread():
    """Hilo dedicado para pyttsx3. Inicializa COM (CoInitialize) en su propio contexto."""
    try:
        import ctypes
        ctypes.windll.ole32.CoInitialize(None)
    except Exception:
        pass  # En plataformas no-Windows simplemente continúa

    engine = None
    if HAS_PYTTSX3:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.setProperty("volume", 1.0)
            try:
                voices = engine.getProperty("voices")
                for voice in voices:
                    nombre = (voice.name or "").lower()
                    if "spanish" in nombre or "es-" in getattr(voice, "id", "").lower():
                        engine.setProperty("voice", voice.id)
                        break
            except Exception:
                pass
            _tts_engine_ref[0] = engine
            log.info("pyttsx3 TTS listo")
        except Exception as e:
            log.warning("pyttsx3 error: %s", e)

    while True:
        item = _tts_queue.get()
        if item is None:
            break  # señal de parada
        texto, done_event = item
        if engine and texto:
            try:
                engine.say(texto)
                engine.runAndWait()
            except Exception as e:
                log.debug("TTS worker error: %s", e)
        if done_event:
            done_event.set()
        _tts_queue.task_done()

    try:
        import ctypes
        ctypes.windll.ole32.CoUninitialize()
    except Exception:
        pass


def _ensure_tts_worker():
    global _tts_worker_started
    with _tts_worker_lock:
        if not _tts_worker_started:
            t = threading.Thread(target=_tts_worker_thread, name="kitian-tts", daemon=True)
            t.start()
            _tts_worker_started = True


def get_tts():
    """Devuelve un objeto TTS compatible con el código legado."""
    _ensure_tts_worker()
    tts = type("TTS", (), {})()
    tts._engine = _tts_engine_ref[0]
    return tts


def texto_a_voz(texto, blocking=True, tts_engine=None):
    """Habla el texto dado usando el worker dedicado de pyttsx3."""
    if not texto:
        return False
    _ensure_tts_worker()
    if not HAS_PYTTSX3:
        log.info("[TTS-SAY] %s", texto)
        return False
    try:
        done_event = threading.Event() if blocking else None
        _tts_queue.put((texto, done_event))
        if blocking and done_event:
            done_event.wait(timeout=30)
        return True
    except Exception as e:
        log.debug("hablar error: %s", e)
    log.info("[TTS-SAY] %s", texto)
    return False


def escuchar_comando(timeout=8):
    if not HAS_SD:
        log.warning("Falta sounddevice para escuchar comandos")
        return None
    try:
        from kitian.audio import VADStream, _get_speaking_engine
    except Exception as e:
        log.warning("Import para VADStream fallo: %s", e)
        return None
    audio_engine = _get_speaking_engine()
    result = {"text": None}

    def on_persona_habla(evento, texto):
        if evento == "vad_text":
            result["text"] = texto

    stream = VADStream(text_cb=on_persona_habla, audio_engine=audio_engine)
    stream.start()
    waited = 0.0
    while waited < timeout and result["text"] is None:
        time.sleep(0.1)
        waited += 0.1
    stream.stop()
    return result["text"]


def escuchar_continuo(modo="simple"):
    return escuchar_comando()


def hablar(texto, blocking=True, audio_engine=None):
    return texto_a_voz(texto, blocking=blocking)


def _get_speaking_engine():
    _ensure_tts_worker()
    return _tts_engine_ref[0]
