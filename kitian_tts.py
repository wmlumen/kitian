import os
import json
import time
import queue
import threading
import numpy as np
import sounddevice as sd
from pathlib import Path

BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "piper_models"
MODEL_PATH = MODEL_DIR / "es_ES-carlfm-x_low.onnx"
CONFIG_PATH = MODEL_DIR / "es_ES-carlfm-x_low.onnx.json"

HAS_PIPER = False
_voice = None

try:
    from piper import PiperVoice
    import onnxruntime
    HAS_PIPER = True
except ImportError:
    pass


class KitianTTS:
    def __init__(self):
        self._voice = None
        self._sample_rate = 22050
        self._speak_lock = threading.Lock()
        self._queue = queue.Queue()
        self._use_piper = HAS_PIPER and MODEL_PATH.exists()

        if self._use_piper:
            try:
                if CONFIG_PATH.exists():
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        config = json.load(f)
                else:
                    config = {"espeak": {"voice": "es"}}

                self._voice = PiperVoice.load(
                    str(MODEL_PATH),
                    config_path=str(CONFIG_PATH) if CONFIG_PATH.exists() else None,
                    use_cuda=False,
                )
                self._sample_rate = self._voice.config.sample_rate
                print(f"  [TTS] Piper cargado: es_ES-carlfm (x-low) @ {self._sample_rate}Hz")
            except Exception as e:
                print(f"  [TTS] Piper fallo: {e}, usando pyttsx3")
                self._use_piper = False

        self._worker = threading.Thread(target=self._voice_worker, daemon=True)
        self._worker.start()

    def _speak_sync(self, texto):
        if self._use_piper and self._voice and texto:
            try:
                with self._speak_lock:
                    audio = b""
                    for chunk in self._voice.synthesize_stream_raw(texto):
                        audio += chunk
                    samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
                    sd.play(samples, self._sample_rate)
                    sd.wait()
                return True
            except Exception:
                return False
        return False

    def _voice_worker(self):
        while True:
            texto = self._queue.get()
            try:
                self._speak_sync(texto)
            finally:
                self._queue.task_done()

    def hablar(self, texto, blocking=True):
        if not texto:
            return False
        if blocking:
            return self._speak_sync(texto)
        self._queue.put(texto)
        return True

    def hablar_streaming(self, texto, blocking=True):
        if self._use_piper and self._voice and texto:
            try:
                with self._speak_lock:
                    for chunk in self._voice.synthesize_stream_raw(texto):
                        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                        sd.play(samples, self._sample_rate)
                        if blocking:
                            sd.wait()
                return True
            except Exception:
                return False
        return False


_tts = None

def get_tts():
    global _tts
    if _tts is None:
        _tts = KitianTTS()
    return _tts


def has_piper():
    return HAS_PIPER and MODEL_PATH.exists()
