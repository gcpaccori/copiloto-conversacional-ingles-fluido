from typing import Optional
import numpy as np

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

class ASREngine:
    def __init__(self, model_size: str = "tiny.en", compute_type: str = "int8"):
        self.model_size = model_size
        self.compute_type = compute_type
        self.model = None
        self.ready = False
        self._init()

    def _init(self):
        if WhisperModel is None:
            return
        try:
            self.model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
            self.ready = True
        except Exception:
            self.ready = False

    def transcribe(self, audio_f32: np.ndarray) -> str:
        if not self.ready or self.model is None:
            return ""
        try:
            segments, _ = self.model.transcribe(
                audio_f32,
                language="en",
                vad_filter=False,
                beam_size=1
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception:
            return ""
