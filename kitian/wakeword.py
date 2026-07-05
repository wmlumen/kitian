import queue
import threading
import time
import numpy as np

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

try:
    from openwakeword.model import Model as OWWModel
    HAS_OWW = True
except Exception:
    HAS_OWW = False


class WakeWordBridge:
    def __init__(self, words=None, threshold: float = 0.5):
        self.words = words or ["kitian"]
        self.threshold = threshold
        self.model = None

    def init(self):
        if not HAS_OWW:
            return False
        try:
            self.model = OWWModel(
                wakeword_models=[f"{w}.tflite" for w in self.words],
                inference_framework="tflite",
            )
            return True
        except Exception:
            return False

    def score(self, frame: np.ndarray):
        if self.model is None:
            return {}
        try:
            pcm = frame.astype(np.float32) / 32768.0
            pcm = pcm.flatten()
            return self.model.predict(pcm=pcm)
        except Exception:
            return {}
