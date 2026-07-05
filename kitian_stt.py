import os
import re
import numpy as np
import sounddevice as sd
from pathlib import Path

BASE_DIR = Path(__file__).parent
SAMPLE_RATE = 16000
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
COMPUTE_TYPE = "int8"

HAS_WHISPER = False
_whisper_model = None

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    pass


def cargar_whisper():
    global _whisper_model
    if not HAS_WHISPER:
        return False
    if _whisper_model is not None:
        return True
    try:
        print(f"  [STT] Cargando Whisper '{MODEL_SIZE}'...")
        _whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
        print(f"  [STT] Whisper '{MODEL_SIZE}' listo")
        return True
    except Exception as e:
        print(f"  [STT] Error cargando Whisper: {e}")
        return False


def transcribir_local(audio_numpy):
    if not HAS_WHISPER or _whisper_model is None:
        return None
    try:
        audio_float = audio_numpy.astype(np.float32) / 32768.0
        segments, _ = _whisper_model.transcribe(
            audio_float,
            language="es",
            beam_size=5,
            vad_filter=True,
            initial_prompt="Asistente de voz en español. La palabra de activación es Kitian.",
        )
        texto = " ".join(s.text for s in segments).strip()
        texto = re.sub(r"\s+", " ", texto)
        return texto if texto else None
    except Exception:
        return None


def grabar_audio(duracion):
    data = sd.rec(
        int(duracion * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocking=True,
    )
    return data.flatten()
