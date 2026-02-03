import os
import queue
import tkinter as tk

import sounddevice as sd

from app.utils.config import load_config
from app.audio.capture import AudioWorker
from app.audio.segmenter import pcm_bytes_to_float32
from app.asr.whisper_asr import ASREngine
from app.coach.embedder import Embedder
from app.coach.translator import TranslatorENES
from app.rag.pdf_store import DocumentStore
from app.llm.llm_engine import LLMEngine
from app.coach.coach import Coach
from app.ui.overlay import OverlayUI
from app.ui.config_window import ConfigWindow

DEFAULT_CFG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.default.json")

class App:
    def __init__(self):
        self.cfg = load_config(DEFAULT_CFG)

        self.root = tk.Tk()
        self.root.withdraw()

        self.overlay = OverlayUI(self.root)
        self.cfg_win = ConfigWindow(self.root, self.cfg, on_apply=self.apply_config)

        self.event_q: queue.Queue = queue.Queue()
        self.ui_q: queue.Queue = queue.Queue()

        self.mic_worker = None
        self.loop_worker = None

        self.embedder = Embedder()
        self.translator = TranslatorENES()
        self.docstore = DocumentStore(self.embedder)

        self.asr = None
        self.llm = None
        self.coach = None

        self.last_partial_t = 0

        # Hotkeys (Tkinter-level)
        self.root.bind_all("<F8>", lambda e: self.overlay.toggle_clickthrough())
        self.root.bind_all("<F9>", lambda e: self.overlay.toggle_visible())
        self.root.bind_all("<F10>", lambda e: self.overlay.set_topmost(True))

        self.apply_config()
        self.root.after(30, self.engine_tick)
        self.root.after(60, self.ui_tick)

        self.cfg_win.win.deiconify()

    def apply_config(self):
        # Rebuild engines
        self.asr = ASREngine(self.cfg.asr_model_size, self.cfg.asr_compute_type)
        self.llm = LLMEngine(self.cfg.llm_model_path, self.cfg.llm_ctx, self.cfg.llm_threads)

        # PDF load
        if self.cfg.enable_document and self.cfg.pdf_path:
            ok = self.docstore.load_pdf(self.cfg.pdf_path)
            if not ok:
                self.ui_q.put({"type":"status","text":"⚠️ No pude cargar el PDF (falta PyMuPDF o ruta inválida)."})
        else:
            self.docstore.chunks, self.docstore.pages, self.docstore.vecs = [], [], None

        self.coach = Coach(
            profile_context=self.cfg.profile_context,
            goal_context=self.cfg.goal_context,
            enable_translation=self.cfg.enable_translation,
            enable_document=self.cfg.enable_document,
            cite_document=self.cfg.cite_document,
            llm=self.llm,
            embedder=self.embedder,
            docstore=self.docstore,
            translator=self.translator
        )

        # Overlay style
        self.overlay.apply_style(
            alpha=self.cfg.overlay_alpha,
            font_size=self.cfg.overlay_font_size,
            x=self.cfg.overlay_pos_x,
            y=self.cfg.overlay_pos_y,
            clickthrough=self.cfg.overlay_click_through
        )

        # Restart workers
        self.stop_workers()
        self.start_workers()

    def start_workers(self):
        if self.cfg.mic_device is None or self.cfg.loopback_device is None:
            self.ui_q.put({"type":"status","text":"Configura mic y loopback en Configuración."})
            return

        self.mic_worker = AudioWorker("me", self.cfg.mic_device, loopback=False, sample_rate=self.cfg.sample_rate, out_q=self.event_q)
        self.loop_worker = AudioWorker("her", self.cfg.loopback_device, loopback=True, sample_rate=self.cfg.sample_rate, out_q=self.event_q)
        self.mic_worker.start()
        self.loop_worker.start()
        self.ui_q.put({"type":"status","text":"✅ Captura activa (mic + loopback)."})

    def stop_workers(self):
        for w in [self.mic_worker, self.loop_worker]:
            if w is not None:
                w.stop()

    def engine_tick(self):
        try:
            for _ in range(40):
                ev = self.event_q.get_nowait()
                self.handle_audio_event(ev)
        except queue.Empty:
            pass
        self.root.after(30, self.engine_tick)

    def handle_audio_event(self, ev):
        if ev.get("kind") == "error":
            self.ui_q.put({"type":"status","text": f"⚠️ Audio error {ev.get('source')}: {ev.get('error')}"})
            return

        source = ev.get("source")  # her/me
        kind = ev.get("kind")
        audio = pcm_bytes_to_float32(ev.get("pcm16", b""))

        if audio.size == 0 or self.asr is None:
            return

        if source == "her":
            if kind == "partial":
                # throttle partials to keep CPU stable
                import time
                t = time.time()
                if (t - self.last_partial_t) < 0.7:
                    return
                self.last_partial_t = t

                txt = self.asr.transcribe(audio)
                if txt:
                    sug = self.coach.suggest_draft(txt)
                    es = self.coach.maybe_translate_her(txt)
                    self.ui_q.put({"type":"her","phase":"partial","en":txt,"es":es,"suggest":sug})

            elif kind == "final":
                txt = self.asr.transcribe(audio)
                if txt:
                    sug = self.coach.suggest_final(txt)
                    es = self.coach.maybe_translate_her(txt)
                    self.ui_q.put({"type":"her","phase":"final","en":txt,"es":es,"suggest":sug})

        elif source == "me":
            if kind == "final":
                txt = self.asr.transcribe(audio)
                if txt:
                    evl = self.coach.evaluate_me(txt)
                    self.ui_q.put({"type":"me","en":txt,"eval":evl})

    def ui_tick(self):
        try:
            while True:
                msg = self.ui_q.get_nowait()
                self.render(msg)
        except queue.Empty:
            pass
        self.root.after(60, self.ui_tick)

    def render(self, msg):
        if msg.get("type") == "status":
            self.overlay.set_text(msg.get("text", ""))
            return

        if msg.get("type") == "her":
            en = msg.get("en", "")
            es = msg.get("es", "")
            sug = msg.get("suggest") or {}
            say = (sug.get("say_now") or "").strip()
            bridge = (sug.get("bridge_now") or "").strip()

            out = []
            out.append("HER:")
            out.append(en)
            if self.cfg.enable_translation and es:
                out.append("")
                out.append("ES:")
                out.append(es)
            if bridge:
                out.append("")
                out.append("BRIDGE:")
                out.append(bridge)
            if say:
                out.append("")
                out.append("SAY NOW:")
                out.append(say)

            self.overlay.set_text("\n".join(out))
            return

        if msg.get("type") == "me":
            en = msg.get("en", "")
            evl = msg.get("eval") or {}
            status = evl.get("status", "ok")
            notes = evl.get("notes", [])
            sug = evl.get("suggest") or {}

            out = []
            out.append("YOU SAID:")
            out.append(en)
            out.append("")
            out.append("✅ OK" if status == "ok" else f"⚠️ {status}")
            if notes:
                out.append("NOTES:")
                out.extend(notes)
            if sug.get("bridge_now"):
                out.append("")
                out.append("BRIDGE:")
                out.append(sug["bridge_now"])
            if sug.get("say_now"):
                out.append("")
                out.append("SAY NOW:")
                out.append(sug["say_now"])

            self.overlay.set_text("\n".join(out))
            return

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
