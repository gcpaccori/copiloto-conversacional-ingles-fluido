import numpy as np
import webrtcvad
from typing import List, Dict, Any

class Segmenter:
    """VAD segmenter: emits partial and final speech segments."""
    def __init__(self, sample_rate: int = 16000, vad_mode: int = 2):
        self.sr = sample_rate
        self.vad = webrtcvad.Vad(vad_mode)
        self.frame_ms = 20
        self.frame_len = int(self.sr * self.frame_ms / 1000)  # 320 @16k
        self.silence_end_ms = 400
        self.partial_every_ms = 800
        self.max_segment_ms = 7000

        self._buf = bytearray()
        self._active = False
        self._segment = bytearray()
        self._silence_ms = 0
        self._last_partial_ms = 0
        self._segment_ms = 0

    def feed(self, pcm16: np.ndarray) -> List[Dict[str, Any]]:
        events = []
        self._buf.extend(pcm16.tobytes())

        while len(self._buf) >= self.frame_len * 2:
            frame = self._buf[: self.frame_len * 2]
            del self._buf[: self.frame_len * 2]

            try:
                is_speech = self.vad.is_speech(frame, self.sr)
            except Exception:
                is_speech = False

            if is_speech:
                if not self._active:
                    self._active = True
                    self._segment = bytearray()
                    self._silence_ms = 0
                    self._last_partial_ms = 0
                    self._segment_ms = 0

                self._segment.extend(frame)
                self._segment_ms += self.frame_ms
                self._silence_ms = 0

                self._last_partial_ms += self.frame_ms
                if self._last_partial_ms >= self.partial_every_ms:
                    self._last_partial_ms = 0
                    events.append({"type": "partial", "pcm16": bytes(self._segment), "ms": self._segment_ms})

                if self._segment_ms >= self.max_segment_ms:
                    events.append({"type": "final", "pcm16": bytes(self._segment), "ms": self._segment_ms})
                    self._active = False
            else:
                if self._active:
                    self._silence_ms += self.frame_ms
                    if self._silence_ms >= self.silence_end_ms:
                        events.append({"type": "final", "pcm16": bytes(self._segment), "ms": self._segment_ms})
                        self._active = False

        return events

def pcm_bytes_to_float32(pcm_bytes: bytes) -> np.ndarray:
    a = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    if a.size == 0:
        return np.zeros((0,), dtype=np.float32)
    return (a / 32768.0).astype(np.float32)
