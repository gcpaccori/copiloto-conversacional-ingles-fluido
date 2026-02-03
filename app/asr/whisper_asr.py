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
            # Optimize for speed: use available CPU threads
            import os
            cpu_threads = os.cpu_count() or 4
            
            self.model = WhisperModel(
                self.model_size, 
                device="cpu", 
                compute_type=self.compute_type,
                cpu_threads=cpu_threads,  # Use all available CPU threads
                num_workers=1             # Single worker for low latency
            )
            self.ready = True
        except Exception as e:
            import sys
            print(f"Warning: Failed to initialize Whisper model '{self.model_size}': {e}", file=sys.stderr)
            self.ready = False

    def transcribe(self, audio_f32: np.ndarray) -> str:
        if not self.ready or self.model is None:
            return ""
        try:
            segments, _ = self.model.transcribe(
                audio_f32,
                language="en",
                vad_filter=False,
                beam_size=1,
                best_of=1,                      # Only use 1 candidate (faster)
                temperature=0.0,                # Greedy sampling (fastest, deterministic)
                condition_on_previous_text=False,  # No context dependency (faster)
                without_timestamps=True,        # Skip timestamp generation (faster)
                log_progress=False              # No progress logging (faster)
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception:
            return ""
