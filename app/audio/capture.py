import time
import queue
import threading
from typing import Optional, Dict, Any

import numpy as np
import sounddevice as sd

from app.audio.segmenter import Segmenter
from app.utils.time import now_ms

class AudioWorker(threading.Thread):
    """Captures audio from a device. If loopback=True, uses WASAPI loopback."""
    def __init__(self, name: str, device: int, loopback: bool, sample_rate: int, out_q: queue.Queue):
        super().__init__(daemon=True)
        self.name = name
        self.device = device
        self.loopback = loopback
        self.sample_rate = sample_rate
        self.out_q = out_q

        self.running = threading.Event()
        self.running.set()

        self.segmenter = Segmenter(sample_rate=sample_rate, vad_mode=2)

    def stop(self):
        self.running.clear()

    def run(self):
        extra = None
        if self.loopback:
            try:
                extra = sd.WasapiSettings(loopback=True)
            except Exception:
                extra = None

        blocksize = int(self.sample_rate * 0.1)  # 100ms
        ch = 1

        def callback(indata, frames, time_info, status):
            if not self.running.is_set():
                raise sd.CallbackStop()

            x = indata[:, 0].copy()
            x = np.clip(x, -1.0, 1.0)
            pcm16 = (x * 32767.0).astype(np.int16)

            for ev in self.segmenter.feed(pcm16):
                self.out_q.put({
                    "source": self.name,
                    "kind": ev["type"],  # partial / final
                    "pcm16": ev["pcm16"],
                    "ms": ev["ms"],
                    "t": now_ms()
                })

        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=ch,
                dtype="float32",
                blocksize=blocksize,
                callback=callback,
                extra_settings=extra
            ):
                while self.running.is_set():
                    time.sleep(0.2)
        except Exception as e:
            self.out_q.put({"source": self.name, "kind": "error", "error": str(e), "t": now_ms()})
