import os
import json
import time
import queue
import threading
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

# Audio
import sounddevice as sd
import webrtcvad

# ASR
try:
    from faster_whisper import WhisperModel
except Exception as e:
    WhisperModel = None

# PDF
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# Optional: embeddings
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# Optional: LLM (GGUF)
try:
    from llama_cpp import Llama
except Exception:
    Llama = None

# Optional: Offline translation
try:
    import argostranslate.package
    import argostranslate.translate
except Exception:
    argostranslate = None

# UI (Tkinter)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# =========================
# Config
# =========================

CONFIG_PATH = "copiloto_config.json"

@dataclass
class AppConfig:
    # Audio device indices
    mic_device: Optional[int] = None
    loopback_device: Optional[int] = None  # output device used as input in WASAPI loopback
    sample_rate: int = 16000

    # ASR
    asr_model_size: str = "tiny.en"  # tiny.en / base.en
    asr_compute_type: str = "int8"   # int8 for CPU speed

    # LLM
    llm_model_path: str = ""  # path to GGUF (optional)
    llm_ctx: int = 2048
    llm_threads: int = max(2, os.cpu_count() or 4)

    # UI
    overlay_alpha: float = 0.28
    overlay_font_size: int = 18
    overlay_pos_x: int = 80
    overlay_pos_y: int = 80

    # Toggles
    enable_translation: bool = False
    enable_document: bool = False
    cite_document: bool = True

    # User context
    profile_context: str = "My name is Gabriel. I work in IT / Cloud / IoT."
    goal_context: str = "Have a smooth professional conversation in English."
    mode: str = "normal"  # normal / training

    # Document
    pdf_path: str = ""

def load_config() -> AppConfig:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig(**data)
        except Exception:
            pass
    return AppConfig()

def save_config(cfg: AppConfig) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


# =========================
# Helpers
# =========================

def now_ms() -> int:
    return int(time.time() * 1000)

def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))

def safe_json_extract(text: str) -> Dict[str, Any]:
    """
    Tries to extract JSON object from model output.
    """
    text = text.strip()
    # naive: find first '{' and last '}'
    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(text[i:j+1])
        except Exception:
            return {}
    return {}


# =========================
# Translation (optional)
# =========================

class TranslatorENES:
    def __init__(self):
        self.ready = False
        self._init_argos()

    def _init_argos(self):
        # Only if argostranslate is installed and a model is installed
        try:
            if argostranslate is None:
                return
            # if language packages exist, translator works
            self.ready = True
        except Exception:
            self.ready = False

    def translate(self, text: str) -> str:
        if not self.ready or argostranslate is None:
            return ""
        try:
            return argostranslate.translate.translate(text, "en", "es")
        except Exception:
            return ""


# =========================
# Embeddings (optional)
# =========================

class Embedder:
    def __init__(self):
        self.model = None
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    def encode(self, text: str) -> Optional[np.ndarray]:
        if self.model is None:
            return None
        v = self.model.encode([text], normalize_embeddings=True)[0]
        return np.asarray(v, dtype=np.float32)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))


# =========================
# PDF RAG (optional)
# =========================

class DocumentStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self.chunks: List[str] = []
        self.vecs: Optional[np.ndarray] = None  # (n, d)
        self.pages: List[int] = []

    def load_pdf(self, pdf_path: str) -> bool:
        if not pdf_path or not os.path.exists(pdf_path):
            return False
        if fitz is None:
            return False

        doc = fitz.open(pdf_path)
        chunks, pages = [], []
        for p in range(len(doc)):
            text = doc[p].get_text("text").strip()
            if not text:
                continue
            # chunking simple
            parts = self._chunk_text(text, chunk_chars=1400, overlap=200)
            for part in parts:
                chunks.append(part)
                pages.append(p + 1)  # 1-indexed
        self.chunks = chunks
        self.pages = pages

        # embeddings if available
        if self.embedder.model is not None and len(self.chunks) > 0:
            vec_list = []
            for c in self.chunks:
                v = self.embedder.encode(c)
                if v is not None:
                    vec_list.append(v)
            if vec_list:
                self.vecs = np.stack(vec_list, axis=0)
        else:
            self.vecs = None
        return True

    @staticmethod
    def _chunk_text(text: str, chunk_chars: int = 1400, overlap: int = 200) -> List[str]:
        text = " ".join(text.split())
        if len(text) <= chunk_chars:
            return [text]
        out = []
        i = 0
        while i < len(text):
            j = min(len(text), i + chunk_chars)
            out.append(text[i:j])
            if j == len(text):
                break
            i = max(0, j - overlap)
        return out

    def retrieve(self, query: str, k: int = 4) -> List[Tuple[str, int, float]]:
        """
        Returns list of (chunk, page, score)
        """
        if not self.chunks:
            return []
        # Embedding retrieval if possible
        qv = self.embedder.encode(query) if self.embedder.model is not None else None
        if qv is not None and self.vecs is not None and self.vecs.shape[0] == len(self.chunks):
            sims = self.vecs @ qv  # cosine because normalized
            idx = np.argsort(-sims)[:k]
            return [(self.chunks[int(i)], self.pages[int(i)], float(sims[int(i)])) for i in idx]
        # fallback keyword scoring
        q = query.lower()
        scored = []
        for c, p in zip(self.chunks, self.pages):
            score = sum(1 for w in q.split() if w in c.lower())
            scored.append((c, p, float(score)))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:k]


# =========================
# LLM (optional GGUF)
# =========================

class LLMEngine:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.llm = None
        self.ready = False
        self._init_llm()

    def _init_llm(self):
        if not self.cfg.llm_model_path:
            return
        if not os.path.exists(self.cfg.llm_model_path):
            return
        if Llama is None:
            return
        try:
            self.llm = Llama(
                model_path=self.cfg.llm_model_path,
                n_ctx=self.cfg.llm_ctx,
                n_threads=self.cfg.llm_threads,
                n_gpu_layers=0,
                verbose=False
            )
            self.ready = True
        except Exception:
            self.ready = False
            self.llm = None

    def generate_json(self, system: str, user: str, max_tokens: int = 80) -> Dict[str, Any]:
        """
        Returns a JSON-like dict. If LLM is not available, uses templates.
        """
        if not self.ready or self.llm is None:
            return {}

        prompt = (
            f"<|system|>\n{system}\n"
            f"<|user|>\n{user}\n"
            f"<|assistant|>\n"
        )
        try:
            out = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=0.2,
                top_p=0.9,
                stop=["<|user|>", "<|system|>"]
            )
            text = out["choices"][0]["text"]
            return safe_json_extract(text)
        except Exception:
            return {}


# =========================
# ASR
# =========================

class ASREngine:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.model = None
        self.ready = False
        self._init()

    def _init(self):
        if WhisperModel is None:
            return
        try:
            self.model = WhisperModel(
                self.cfg.asr_model_size,
                device="cpu",
                compute_type=self.cfg.asr_compute_type
            )
            self.ready = True
        except Exception:
            self.ready = False

    def transcribe(self, audio_f32: np.ndarray) -> str:
        """
        audio_f32: float32 mono 16kHz in [-1,1]
        """
        if not self.ready or self.model is None:
            return ""
        # Keep it fast: short segments, no beam search
        try:
            segments, _info = self.model.transcribe(
                audio_f32,
                language="en",
                vad_filter=False,
                beam_size=1
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception:
            return ""


# =========================
# VAD + Segmenter
# =========================

class Segmenter:
    """
    Converts continuous audio stream into "speech segments" + optional partial emissions.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sr = sample_rate
        self.vad = webrtcvad.Vad(2)  # 0-3 (agresivo = 3)
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
        """
        pcm16: int16 mono array for a small block (e.g. 100ms)
        Returns events: [{"type": "partial"/"final", "pcm16": bytes, "ms": int}, ...]
        """
        events = []
        self._buf.extend(pcm16.tobytes())

        while len(self._buf) >= self.frame_len * 2:
            frame = self._buf[: self.frame_len * 2]
            del self._buf[: self.frame_len * 2]

            is_speech = False
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

                # partial emission
                self._last_partial_ms += self.frame_ms
                if self._last_partial_ms >= self.partial_every_ms:
                    self._last_partial_ms = 0
                    events.append({"type": "partial", "pcm16": bytes(self._segment), "ms": self._segment_ms})

                # force finalize if too long
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


# =========================
# Coach (state + logic)
# =========================

class Coach:
    def __init__(self, cfg: AppConfig, llm: LLMEngine, embedder: Embedder, docstore: DocumentStore, translator: TranslatorENES):
        self.cfg = cfg
        self.llm = llm
        self.embedder = embedder
        self.docstore = docstore
        self.translator = translator

        self.history: List[Tuple[str, str]] = []  # (speaker, text)
        self.summary: str = ""
        self.topic_vec: Optional[np.ndarray] = None
        self.goal: str = cfg.goal_context

        self.last_suggest: Dict[str, Any] = {}
        self.last_her_text: str = ""
        self.last_me_text: str = ""

        # cached template responses by intent
        self.templates = {
            "ask_experience": "Sure. I have experience with cloud services and IoT systems. What would you like to focus on first?",
            "ask_schedule": "Yes, I’m available. What schedule and time zone overlap do you need?",
            "clarify": "Got it—could you clarify what you mean by that?",
            "confirm": "Just to confirm, you mean {x}, right?",
            "generic": "Understood. Here’s what I can do: {x}."
        }

    def _update_topic(self, text: str):
        v = self.embedder.encode(text)
        if v is not None:
            self.topic_vec = v

    def _topic_shift(self, me_text: str) -> bool:
        if self.topic_vec is None:
            return False
        v = self.embedder.encode(me_text)
        if v is None:
            # fallback heuristic
            return ("anyway" in me_text.lower()) or ("by the way" in me_text.lower()) or ("also" in me_text.lower())
        sim = Embedder.cosine(v, self.topic_vec)
        # threshold tuned for normalized embeddings
        return sim < 0.45

    def _intent_fast(self, her_text: str) -> str:
        t = her_text.lower()
        if any(k in t for k in ["experience", "background", "worked", "project", "built"]):
            return "ask_experience"
        if any(k in t for k in ["schedule", "available", "availability", "time zone", "timezone", "hours"]):
            return "ask_schedule"
        if any(k in t for k in ["confirm", "right?", "correct", "is that"]):
            return "confirm"
        if any(k in t for k in ["clarify", "mean", "explain", "what do you mean"]):
            return "clarify"
        if "?" in t:
            return "generic"
        return "generic"

    def _system_prompt(self) -> str:
        return (
            "You are a real-time conversation copilot. Output STRICT JSON only.\n"
            "Your job: give the user one short sentence to say NOW in English, and optionally a bridge if topic shifts.\n"
            "Never write long paragraphs. Max 2 sentences in 'say_now'.\n"
            "Return JSON keys: say_now, intent, must_include (array), bridge_now (optional), next_if_yes (optional), next_if_no (optional).\n"
        )

    def _build_user_prompt(self, her_text: str, me_text_partial: str = "", retrieved: str = "") -> str:
        hist = "\n".join([f"{spk.upper()}: {txt}" for spk, txt in self.history[-6:]])
        doc_part = f"\nDOCUMENT_CONTEXT:\n{retrieved}\n" if retrieved else ""
        return (
            f"PROFILE:\n{self.cfg.profile_context}\n\n"
            f"GOAL:\n{self.cfg.goal_context}\n\n"
            f"RECENT:\n{hist}\n\n"
            f"HER_LATEST:\n{her_text}\n\n"
            f"MY_PARTIAL:\n{me_text_partial}\n"
            f"{doc_part}\n"
            f"Write only JSON."
        )

    def suggest_for_her_partial(self, her_partial: str) -> Dict[str, Any]:
        """
        Draft suggestion while she is still talking.
        Keep it very short and safe.
        """
        if not her_partial.strip():
            return {}

        intent = self._intent_fast(her_partial)
        # Draft: templates first (zero-latency feel)
        draft = {"say_now": self.templates.get(intent, self.templates["generic"]), "intent": intent, "must_include": []}

        # If LLM ready, refine into JSON quickly
        retrieved_text = ""
        if self.cfg.enable_document and self.docstore.chunks:
            # only retrieve if it looks like user is citing
            if any(k in her_partial.lower() for k in ["according to", "report", "document", "pdf", "study"]):
                hits = self.docstore.retrieve(her_partial, k=3)
                retrieved_text = "\n".join([f"(p.{p}) {c[:500]}" for c, p, _ in hits])

        if self.llm.ready:
            out = self.llm.generate_json(self._system_prompt(), self._build_user_prompt(her_partial, "", retrieved_text), max_tokens=70)
            if out.get("say_now"):
                return out
        return draft

    def finalize_for_her(self, her_final: str) -> Dict[str, Any]:
        if not her_final.strip():
            return {}

        self.last_her_text = her_final
        self.history.append(("her", her_final))
        self._update_topic(her_final)

        retrieved_text = ""
        if self.cfg.enable_document and self.docstore.chunks:
            hits = self.docstore.retrieve(her_final, k=3)
            retrieved_text = "\n".join([f"(p.{p}) {c[:600]}" for c, p, _ in hits])

        intent = self._intent_fast(her_final)
        fallback = {"say_now": self.templates.get(intent, self.templates["generic"]), "intent": intent, "must_include": []}

        if self.llm.ready:
            out = self.llm.generate_json(self._system_prompt(), self._build_user_prompt(her_final, "", retrieved_text), max_tokens=90)
            if out.get("say_now"):
                self.last_suggest = out
                return out

        self.last_suggest = fallback
        return fallback

    def evaluate_my_final(self, me_final: str) -> Dict[str, Any]:
        """
        Compare what user said vs last suggestion.
        Returns: {status, notes, say_now(optional)} to continue.
        """
        if not me_final.strip():
            return {}

        self.last_me_text = me_final
        self.history.append(("me", me_final))

        notes = []
        status = "ok"

        # Topic shift detection
        if self._topic_shift(me_final):
            status = "topic_shift"
            notes.append("Topic shift detected. Generating a bridge + new line.")

        # Simple semantic compare if embeddings available
        sim = None
        if self.embedder.model is not None and self.last_suggest.get("say_now"):
            a = self.embedder.encode(me_final)
            b = self.embedder.encode(self.last_suggest.get("say_now", ""))
            if a is not None and b is not None:
                sim = Embedder.cosine(a, b)
                if sim < 0.42 and status != "topic_shift":
                    status = "needs_alignment"
                    notes.append("Your reply diverged from the suggested intent.")

        # Slot checking (very simple: keyword contains)
        must = self.last_suggest.get("must_include", []) or []
        missing = []
        for m in must:
            if isinstance(m, str) and m and m.lower() not in me_final.lower():
                missing.append(m)
        if missing:
            status = "missing_slots"
            notes.append(f"Missing: {', '.join(missing)}")

        # If topic shift: generate bridge + new suggestion
        if status == "topic_shift":
            bridge = "Before we switch topics, just to wrap up: "
            last = self.last_suggest.get("say_now", "").strip()
            bridge_now = (bridge + (last[:120] + ("..." if len(last) > 120 else ""))).strip()

            # quick new line (ask what they need)
            say_now = "Sure—switching topics. What would you like to discuss next?"
            if self.llm.ready:
                # Use my text as the signal for new topic
                out = self.llm.generate_json(
                    self._system_prompt(),
                    self._build_user_prompt(self.last_her_text, me_final, ""),
                    max_tokens=80
                )
                if out.get("say_now"):
                    out["bridge_now"] = out.get("bridge_now") or bridge_now
                    return {"status": status, "notes": notes, "suggest": out, "sim": sim}
            return {"status": status, "notes": notes, "suggest": {"bridge_now": bridge_now, "say_now": say_now}, "sim": sim}

        return {"status": status, "notes": notes, "sim": sim}

    def maybe_translate_her(self, text: str) -> str:
        if not self.cfg.enable_translation:
            return ""
        return self.translator.translate(text) if self.translator else ""


# =========================
# Audio worker threads
# =========================

class AudioWorker(threading.Thread):
    def __init__(self, name: str, device: int, loopback: bool, cfg: AppConfig, out_q: queue.Queue):
        super().__init__(daemon=True)
        self.name = name
        self.device = device
        self.loopback = loopback
        self.cfg = cfg
        self.out_q = out_q

        self.running = threading.Event()
        self.running.set()

        self.segmenter = Segmenter(sample_rate=cfg.sample_rate)

    def stop(self):
        self.running.clear()

    def run(self):
        # Use WASAPI loopback when needed
        extra = None
        if self.loopback:
            try:
                extra = sd.WasapiSettings(loopback=True)
            except Exception:
                extra = None

        blocksize = int(self.cfg.sample_rate * 0.1)  # 100ms blocks
        ch = 1

        def callback(indata, frames, time_info, status):
            if not self.running.is_set():
                raise sd.CallbackStop()

            # indata float32 -> int16
            x = indata[:, 0].copy()
            x = np.clip(x, -1.0, 1.0)
            pcm16 = (x * 32767.0).astype(np.int16)

            events = self.segmenter.feed(pcm16)
            for ev in events:
                self.out_q.put({
                    "source": self.name,
                    "kind": ev["type"],   # partial / final
                    "pcm16": ev["pcm16"],
                    "ms": ev["ms"],
                    "t": now_ms()
                })

        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.cfg.sample_rate,
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


# =========================
# UI
# =========================

class OverlayUI:
    def __init__(self, root: tk.Tk, cfg: AppConfig):
        self.root = root
        self.cfg = cfg

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", clamp(cfg.overlay_alpha, 0.12, 0.95))
        self.win.configure(bg="black")

        self.label = tk.Label(
            self.win,
            text="",
            fg="white",
            bg="black",
            justify="left",
            font=("Segoe UI", cfg.overlay_font_size, "bold"),
            wraplength=520
        )
        self.label.pack(padx=10, pady=8)

        self._move(cfg.overlay_pos_x, cfg.overlay_pos_y)

    def _move(self, x: int, y: int):
        self.win.geometry(f"+{x}+{y}")

    def set_alpha(self, a: float):
        self.win.attributes("-alpha", clamp(a, 0.12, 0.95))

    def set_text(self, text: str):
        self.label.config(text=text)

    def update_from_cfg(self):
        self.set_alpha(self.cfg.overlay_alpha)
        self.label.config(font=("Segoe UI", self.cfg.overlay_font_size, "bold"))
        self._move(self.cfg.overlay_pos_x, self.cfg.overlay_pos_y)


class ConfigUI:
    def __init__(self, root: tk.Tk, cfg: AppConfig, on_apply):
        self.root = root
        self.cfg = cfg
        self.on_apply = on_apply

        self.win = tk.Toplevel(root)
        self.win.title("Copiloto - Configuración")
        self.win.geometry("860x620")

        # Tabs
        nb = ttk.Notebook(self.win)
        nb.pack(fill="both", expand=True)

        self.tab_audio = ttk.Frame(nb)
        self.tab_context = ttk.Frame(nb)
        self.tab_features = ttk.Frame(nb)

        nb.add(self.tab_audio, text="Audio/ASR")
        nb.add(self.tab_context, text="Contexto")
        nb.add(self.tab_features, text="Funciones")

        self._build_audio_tab()
        self._build_context_tab()
        self._build_features_tab()

        bottom = ttk.Frame(self.win)
        bottom.pack(fill="x", padx=10, pady=10)
        ttk.Button(bottom, text="Guardar & Aplicar", command=self.apply).pack(side="right")
        ttk.Button(bottom, text="Cerrar", command=self.win.withdraw).pack(side="right", padx=8)

    def _device_list(self) -> List[Tuple[int, str]]:
        devs = sd.query_devices()
        out = []
        for i, d in enumerate(devs):
            name = f"{i}: {d['name']} (in={d['max_input_channels']}, out={d['max_output_channels']})"
            out.append((i, name))
        return out

    def _build_audio_tab(self):
        frm = self.tab_audio
        frm.columnconfigure(1, weight=1)

        devices = self._device_list()
        dev_names = [n for _, n in devices]

        ttk.Label(frm, text="Micrófono (tu voz):").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.mic_var = tk.StringVar(value="")
        self.mic_combo = ttk.Combobox(frm, values=dev_names, textvariable=self.mic_var)
        self.mic_combo.grid(row=0, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frm, text="Loopback (audio Teams / sistema):").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.loop_var = tk.StringVar(value="")
        self.loop_combo = ttk.Combobox(frm, values=dev_names, textvariable=self.loop_var)
        self.loop_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frm, text="ASR model (CPU):").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.asr_model = tk.StringVar(value=self.cfg.asr_model_size)
        ttk.Combobox(frm, values=["tiny.en", "base.en"], textvariable=self.asr_model, width=20)\
            .grid(row=2, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frm, text="Sample rate:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.sr_var = tk.IntVar(value=self.cfg.sample_rate)
        ttk.Entry(frm, textvariable=self.sr_var, width=12).grid(row=3, column=1, sticky="w", padx=10, pady=8)

        # preload current device selection if set
        if self.cfg.mic_device is not None:
            self.mic_var.set(dev_names[self.cfg.mic_device] if self.cfg.mic_device < len(dev_names) else "")
        if self.cfg.loopback_device is not None:
            self.loop_var.set(dev_names[self.cfg.loopback_device] if self.cfg.loopback_device < len(dev_names) else "")

        hint = (
            "Tip: Para loopback, selecciona el dispositivo de SALIDA donde escuchas Teams.\n"
            "El sistema usará WASAPI loopback para capturarlo.\n"
            "Si no funciona, necesitas 'Stereo Mix' o un driver virtual (VB-Cable)."
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=10)

    def _build_context_tab(self):
        frm = self.tab_context
        frm.columnconfigure(0, weight=1)

        ttk.Label(frm, text="Quién eres (perfil):").pack(anchor="w", padx=10, pady=(10, 4))
        self.profile_txt = tk.Text(frm, height=8)
        self.profile_txt.pack(fill="x", padx=10)
        self.profile_txt.insert("1.0", self.cfg.profile_context)

        ttk.Label(frm, text="Objetivo de esta conversación (tema/meta):").pack(anchor="w", padx=10, pady=(10, 4))
        self.goal_txt = tk.Text(frm, height=5)
        self.goal_txt.pack(fill="x", padx=10)
        self.goal_txt.insert("1.0", self.cfg.goal_context)

        ttk.Label(frm, text="Modo:").pack(anchor="w", padx=10, pady=(10, 4))
        self.mode_var = tk.StringVar(value=self.cfg.mode)
        ttk.Combobox(frm, values=["normal", "training"], textvariable=self.mode_var, width=14).pack(anchor="w", padx=10)

    def _build_features_tab(self):
        frm = self.tab_features
        frm.columnconfigure(1, weight=1)

        self.tr_var = tk.BooleanVar(value=self.cfg.enable_translation)
        ttk.Checkbutton(frm, text="Traducción EN→ES (lo que dice ella)", variable=self.tr_var)\
            .grid(row=0, column=0, sticky="w", padx=10, pady=8)

        self.doc_var = tk.BooleanVar(value=self.cfg.enable_document)
        ttk.Checkbutton(frm, text="Usar PDF como fuente (RAG)", variable=self.doc_var)\
            .grid(row=1, column=0, sticky="w", padx=10, pady=8)

        self.cite_var = tk.BooleanVar(value=self.cfg.cite_document)
        ttk.Checkbutton(frm, text="Citar página del PDF en pantalla", variable=self.cite_var)\
            .grid(row=2, column=0, sticky="w", padx=10, pady=8)

        ttk.Label(frm, text="PDF:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.pdf_var = tk.StringVar(value=self.cfg.pdf_path)
        ttk.Entry(frm, textvariable=self.pdf_var).grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frm, text="Cargar…", command=self.pick_pdf).grid(row=3, column=2, padx=10, pady=8)

        ttk.Separator(frm).grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        ttk.Label(frm, text="LLM (GGUF) opcional:").grid(row=5, column=0, sticky="w", padx=10, pady=6)
        self.llm_var = tk.StringVar(value=self.cfg.llm_model_path)
        ttk.Entry(frm, textvariable=self.llm_var).grid(row=5, column=1, sticky="ew", padx=10, pady=6)
        ttk.Button(frm, text="Elegir…", command=self.pick_llm).grid(row=5, column=2, padx=10, pady=6)

        ttk.Separator(frm).grid(row=6, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        ttk.Label(frm, text="Overlay (casi invisible):").grid(row=7, column=0, sticky="w", padx=10, pady=6)
        self.alpha_var = tk.DoubleVar(value=self.cfg.overlay_alpha)
        ttk.Scale(frm, from_=0.12, to=0.95, variable=self.alpha_var, orient="horizontal")\
            .grid(row=7, column=1, sticky="ew", padx=10, pady=6)

        ttk.Label(frm, text="Tamaño letra:").grid(row=8, column=0, sticky="w", padx=10, pady=6)
        self.font_var = tk.IntVar(value=self.cfg.overlay_font_size)
        ttk.Spinbox(frm, from_=12, to=38, textvariable=self.font_var, width=8)\
            .grid(row=8, column=1, sticky="w", padx=10, pady=6)

        pos = ttk.Frame(frm)
        pos.grid(row=9, column=0, columnspan=3, sticky="w", padx=10, pady=6)
        ttk.Label(pos, text="Pos X:").pack(side="left")
        self.posx_var = tk.IntVar(value=self.cfg.overlay_pos_x)
        ttk.Entry(pos, textvariable=self.posx_var, width=6).pack(side="left", padx=6)
        ttk.Label(pos, text="Pos Y:").pack(side="left")
        self.posy_var = tk.IntVar(value=self.cfg.overlay_pos_y)
        ttk.Entry(pos, textvariable=self.posy_var, width=6).pack(side="left", padx=6)

        hint = (
            "Tip: Si no tienes LLM, el sistema igual funciona con plantillas rápidas.\n"
            "Si cargas un GGUF (Qwen 0.5B), las sugerencias serán más personalizadas."
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=10, column=0, columnspan=3, sticky="w", padx=10, pady=10)

    def pick_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_var.set(path)

    def pick_llm(self):
        path = filedialog.askopenfilename(filetypes=[("GGUF model", "*.gguf")])
        if path:
            self.llm_var.set(path)

    def _parse_selected_index(self, combo_text: str) -> Optional[int]:
        if not combo_text:
            return None
        # "12: Device Name..."
        try:
            head = combo_text.split(":", 1)[0].strip()
            return int(head)
        except Exception:
            return None

    def apply(self):
        self.cfg.mic_device = self._parse_selected_index(self.mic_var.get())
        self.cfg.loopback_device = self._parse_selected_index(self.loop_var.get())
        self.cfg.asr_model_size = self.asr_model.get().strip()
        self.cfg.sample_rate = int(self.sr_var.get())

        self.cfg.profile_context = self.profile_txt.get("1.0", "end").strip()
        self.cfg.goal_context = self.goal_txt.get("1.0", "end").strip()
        self.cfg.mode = self.mode_var.get().strip()

        self.cfg.enable_translation = bool(self.tr_var.get())
        self.cfg.enable_document = bool(self.doc_var.get())
        self.cfg.cite_document = bool(self.cite_var.get())

        self.cfg.pdf_path = self.pdf_var.get().strip()
        self.cfg.llm_model_path = self.llm_var.get().strip()

        self.cfg.overlay_alpha = float(self.alpha_var.get())
        self.cfg.overlay_font_size = int(self.font_var.get())
        self.cfg.overlay_pos_x = int(self.posx_var.get())
        self.cfg.overlay_pos_y = int(self.posy_var.get())

        save_config(self.cfg)
        self.on_apply()


# =========================
# Orchestrator
# =========================

class App:
    def __init__(self):
        self.cfg = load_config()

        self.root = tk.Tk()
        self.root.withdraw()  # hide root; we use toplevels

        self.overlay = OverlayUI(self.root, self.cfg)

        self.event_q: queue.Queue = queue.Queue()
        self.ui_q: queue.Queue = queue.Queue()

        self.asr = ASREngine(self.cfg)
        self.embedder = Embedder()
        self.docstore = DocumentStore(self.embedder)
        self.translator = TranslatorENES()
        self.llm = LLMEngine(self.cfg)
        self.coach = Coach(self.cfg, self.llm, self.embedder, self.docstore, self.translator)

        self.cfg_ui = ConfigUI(self.root, self.cfg, on_apply=self.apply_config)

        self.mic_worker: Optional[AudioWorker] = None
        self.loop_worker: Optional[AudioWorker] = None

        self.last_partial_suggest_t = 0

        # start engine loop
        self.apply_config()
        self.root.after(60, self.ui_tick)
        self.root.after(30, self.engine_tick)

    def apply_config(self):
        # refresh components that depend on config
        self.overlay.update_from_cfg()

        # reload ASR if model changed
        self.asr = ASREngine(self.cfg)

        # reload LLM if path changed
        self.llm = LLMEngine(self.cfg)

        # reload coach references
        self.coach = Coach(self.cfg, self.llm, self.embedder, self.docstore, self.translator)

        # load pdf if enabled and path set
        if self.cfg.enable_document and self.cfg.pdf_path:
            ok = self.docstore.load_pdf(self.cfg.pdf_path)
            if not ok:
                self.ui_q.put({"type": "status", "text": "⚠️ PDF no cargó (falta PyMuPDF o path inválido)."})
        else:
            self.docstore.chunks = []
            self.docstore.vecs = None
            self.docstore.pages = []

        # restart audio workers
        self.stop_workers()
        self.start_workers()

    def start_workers(self):
        if self.cfg.mic_device is None or self.cfg.loopback_device is None:
            self.ui_q.put({"type": "status", "text": "Configura mic y loopback en la ventana de configuración."})
            return

        self.mic_worker = AudioWorker("me", self.cfg.mic_device, loopback=False, cfg=self.cfg, out_q=self.event_q)
        self.loop_worker = AudioWorker("her", self.cfg.loopback_device, loopback=True, cfg=self.cfg, out_q=self.event_q)

        self.mic_worker.start()
        self.loop_worker.start()
        self.ui_q.put({"type": "status", "text": "✅ Audio workers activos."})

    def stop_workers(self):
        for w in [self.mic_worker, self.loop_worker]:
            if w is not None:
                w.stop()

    def engine_tick(self):
        # drain events quickly
        try:
            for _ in range(30):
                ev = self.event_q.get_nowait()
                self.handle_audio_event(ev)
        except queue.Empty:
            pass

        self.root.after(30, self.engine_tick)

    def handle_audio_event(self, ev: Dict[str, Any]):
        if ev.get("kind") == "error":
            self.ui_q.put({"type": "status", "text": f"⚠️ Audio error {ev.get('source')}: {ev.get('error')}"})
            return

        source = ev.get("source")  # "her" or "me"
        kind = ev.get("kind")      # "partial" or "final"
        pcm = ev.get("pcm16", b"")

        audio = pcm_bytes_to_float32(pcm)
        if audio.size == 0:
            return

        if source == "her":
            if kind == "partial":
                # To feel instant: ASR partial not every single time (CPU)
                if now_ms() - self.last_partial_suggest_t < 700:
                    return
                self.last_partial_suggest_t = now_ms()

                text = self.asr.transcribe(audio)
                if text:
                    suggest = self.coach.suggest_for_her_partial(text)
                    tr = self.coach.maybe_translate_her(text)
                    self.ui_q.put({"type": "her_partial", "en": text, "es": tr, "suggest": suggest})

            elif kind == "final":
                text = self.asr.transcribe(audio)
                if text:
                    suggest = self.coach.finalize_for_her(text)
                    tr = self.coach.maybe_translate_her(text)
                    self.ui_q.put({"type": "her_final", "en": text, "es": tr, "suggest": suggest})

        elif source == "me":
            # For me we usually only need FINAL for evaluation (less CPU)
            if kind == "final":
                text = self.asr.transcribe(audio)
                if text:
                    evalr = self.coach.evaluate_my_final(text)
                    self.ui_q.put({"type": "me_final", "en": text, "eval": evalr})

    def ui_tick(self):
        # update overlay with newest meaningful message
        try:
            while True:
                msg = self.ui_q.get_nowait()
                self.render(msg)
        except queue.Empty:
            pass
        self.root.after(60, self.ui_tick)

    def render(self, msg: Dict[str, Any]):
        t = msg.get("type")
        if t == "status":
            self.overlay.set_text(msg.get("text", ""))
            return

        if t in ("her_partial", "her_final"):
            en = msg.get("en", "")
            es = msg.get("es", "")
            suggest = msg.get("suggest") or {}
            say_now = (suggest.get("say_now") or "").strip()
            bridge = (suggest.get("bridge_now") or "").strip()

            lines = []
            lines.append("HER:")
            lines.append(en)
            if self.cfg.enable_translation and es:
                lines.append("")
                lines.append("ES:")
                lines.append(es)

            if bridge:
                lines.append("")
                lines.append("BRIDGE:")
                lines.append(bridge)

            if say_now:
                lines.append("")
                lines.append("SAY NOW:")
                lines.append(say_now)

            self.overlay.set_text("\n".join(lines))
            return

        if t == "me_final":
            me = msg.get("en", "")
            ev = msg.get("eval") or {}
            status = ev.get("status", "ok")
            notes = ev.get("notes", [])
            suggest = ev.get("suggest") or {}

            lines = []
            lines.append("YOU SAID:")
            lines.append(me)
            lines.append("")
            if status == "ok":
                lines.append("✅ OK")
            else:
                lines.append(f"⚠️ {status}")
            if notes:
                lines.append("NOTES:")
                lines.extend(notes)

            if suggest.get("bridge_now"):
                lines.append("")
                lines.append("BRIDGE:")
                lines.append(suggest["bridge_now"])
            if suggest.get("say_now"):
                lines.append("")
                lines.append("SAY NOW:")
                lines.append(suggest["say_now"])

            self.overlay.set_text("\n".join(lines))
            return

    def run(self):
        # show config window initially
        self.cfg_ui.win.deiconify()
        self.root.mainloop()


# =========================
# Entry point
# =========================

if __name__ == "__main__":
    app = App()
    app.run()
