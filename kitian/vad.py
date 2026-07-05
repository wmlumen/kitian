import logging
import threading
import collections
import time
import numpy as np

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

try:
    import torch
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

try:
    from silero_vad import load_silero_vad, VADIterator
    HAS_SILERO_VAD = True
except Exception:
    HAS_SILERO_VAD = False

SAMPLE_RATE = 16000
FRAME_MS = 32
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
MAX_SILENCE_S = 0.9
MAX_SPEECH_S = 6.0

log = logging.getLogger("kitian")


class SileroVADBridge:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.model = None
        self.it = None
        self._lock = threading.Lock()

    def init(self):
        if not (HAS_SILERO_VAD and HAS_SD):
            return False
        try:
            self.model = load_silero_vad()
            self.it = VADIterator(
                self.model,
                threshold=self.threshold,
                sampling_rate=SAMPLE_RATE,
                min_silence_duration_ms=int(MAX_SILENCE_S * 1000),
                speech_pad_ms=100,
            )
            return True
        except Exception as e:
            log.warning("VAD init failed: %s", e)
            return False

    def reset(self):
        if self.it is not None:
            try:
                self.it.reset_states()
            except Exception:
                pass

    def process_frame(self, frame: np.ndarray):
        if self.it is None:
            return None
        try:
            with self._lock:
                return self.it(input_tensor=torch.from_numpy(frame).float(), return_seconds=True)
        except Exception:
            return None


_stream_ctx = {"stream": None, "queue": collections.deque(maxlen=128), "lock": threading.Lock(), "active": False}


def _audio_callback(indata, frames, time_info, status):
    if status:
        log.debug("audio callback status: %s", status)
    mono = indata[:, 0]
    q = _stream_ctx["queue"]
    lk = _stream_ctx["lock"]
    with lk:
        q.extend(mono.tolist())


def _ensure_stream():
    if not HAS_SD:
        return False
    if _stream_ctx["stream"] is not None and _stream_ctx["active"]:
        return True
    try:
        _stream_ctx["stream"] = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=_audio_callback,
        )
        _stream_ctx["stream"].start()
        _stream_ctx["active"] = True
        return True
    except Exception as e:
        log.warning("No pude iniciar stream de audio: %s", e)
        _stream_ctx["active"] = False
        return False


def _stop_stream():
    try:
        if _stream_ctx["stream"] is not None:
            _stream_ctx["stream"].stop()
            _stream_ctx["stream"].close()
    except Exception:
        pass
    _stream_ctx["stream"] = None
    _stream_ctx["active"] = False
    with _stream_ctx["lock"]:
        _stream_ctx["queue"].clear()


def _drain_frame(vad: SileroVADBridge):
    q = _stream_ctx["queue"]
    lk = _stream_ctx["lock"]
    needed = FRAME_SAMPLES
    out = []
    start = time.time()
    timeout = MAX_SPEECH_S + 1.0
    with lk:
        while len(out) < needed and (time.time() - start) < timeout:
            if len(q) >= (needed - len(out)):
                take = (needed - len(out))
                out.extend([q.popleft() for _ in range(take)])
            else:
                time.sleep(0.005)
    if not out:
        return None
    arr = np.asarray(out, dtype=np.int16)
    return arr


def escuchar_con_vad(vad: SileroVADBridge, speech_cb=None):
    if not _ensure_stream():
        return None
    vad.reset()
    collected = []
    started = False
    start = time.time()
    while True:
        frame = _drain_frame(vad)
        if frame is None:
            break
        speech = vad.process_frame(frame)
        if speech is None:
            continue
        if isinstance(speech, dict):
            if speech.get("start") and not started:
                started = True
                collected = []
                if speech_cb:
                    speech_cb("start")
            if started and speech.get("end") is False and "chunks" in speech:
                chunk = speech.get("chunks", [])
                if chunk:
                    collected.extend(chunk)
            if speech.get("end") and started:
                break
        if not started and (time.time() - start) > MAX_SPEECH_S:
            break
        if started and (time.time() - start) > MAX_SPEECH_S:
            break
    _stop_stream()
    if not collected:
        return None
    arr = np.asarray(collected, dtype=np.int16)
    return arr


def stop_stream():
    _stop_stream()
