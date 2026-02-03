from typing import Optional
import numpy as np
import os
import sys
from pathlib import Path

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

class ASREngine:
    def __init__(self, model_size: str = "Systran/faster-whisper-tiny.en", compute_type: str = "int8"):
        self.model_size = model_size
        self.compute_type = compute_type
        self.model = None
        self.ready = False
        self._init()

    def _resolve_model_path(self, model_size: str) -> str:
        """
        Resolve model path: try local directory first, then return repo ID for download.
        
        Args:
            model_size: Either a HuggingFace repo ID (e.g., "Systran/faster-whisper-tiny.en")
                       or a local path
        
        Returns:
            Local path if exists, otherwise the original model_size for HuggingFace download
        """
        # If it's already a local path that exists, use it
        if os.path.exists(model_size):
            return model_size
        
        # Try to construct local path from repo ID
        # E.g., "Systran/faster-whisper-tiny.en" -> "models/faster-whisper-tiny.en"
        if "/" in model_size:
            model_name = model_size.split("/")[-1]
            local_path = os.path.join("models", model_name)
            if os.path.exists(local_path):
                print(f"Using local model: {local_path}", file=sys.stderr)
                return local_path
        
        # Return the original for HuggingFace download
        return model_size

    def _init(self):
        if WhisperModel is None:
            return
        try:
            import sys
            
            # Resolve model path (local or HuggingFace)
            model_path = self._resolve_model_path(self.model_size)
            
            # Optimize for speed: use available CPU threads
            cpu_threads = os.cpu_count() or 4
            
            print(f"Loading ASR model: {model_path}", file=sys.stderr)
            
            self.model = WhisperModel(
                model_path, 
                device="cpu", 
                compute_type=self.compute_type,
                cpu_threads=cpu_threads,  # Use all available CPU threads
                num_workers=1             # Single worker for low latency
            )
            self.ready = True
            print(f"✅ ASR model loaded successfully", file=sys.stderr)
        except Exception as e:
            import sys
            error_msg = str(e)
            
            # Check for network/domain issues
            if "No address associated with hostname" in error_msg or "ConnectError" in error_msg:
                print(f"❌ Network error: Failed to download model '{self.model_size}'", file=sys.stderr)
                print(f"   The domain may be blocked or unavailable.", file=sys.stderr)
                print(f"   Error: {error_msg}", file=sys.stderr)
            else:
                print(f"❌ Failed to initialize Whisper model '{self.model_size}': {e}", file=sys.stderr)
            
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
