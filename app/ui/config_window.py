import tkinter as tk
from tkinter import ttk, filedialog
import sounddevice as sd

from app.utils.config import AppConfig, save_config

class ConfigWindow:
    def __init__(self, root: tk.Tk, cfg: AppConfig, on_apply):
        self.root = root
        self.cfg = cfg
        self.on_apply = on_apply

        self.win = tk.Toplevel(root)
        self.win.title("Copiloto - Configuración")
        self.win.geometry("880x640")

        nb = ttk.Notebook(self.win)
        nb.pack(fill="both", expand=True)

        self.tab_audio = ttk.Frame(nb)
        self.tab_context = ttk.Frame(nb)
        self.tab_features = ttk.Frame(nb)

        nb.add(self.tab_audio, text="Audio/ASR")
        nb.add(self.tab_context, text="Contexto")
        nb.add(self.tab_features, text="Funciones")

        self._build_audio()
        self._build_context()
        self._build_features()

        bottom = ttk.Frame(self.win)
        bottom.pack(fill="x", padx=10, pady=10)
        ttk.Button(bottom, text="Guardar & Aplicar", command=self.apply).pack(side="right")
        ttk.Button(bottom, text="Cerrar", command=self.win.withdraw).pack(side="right", padx=8)

    def _devices(self):
        devs = sd.query_devices()
        out = []
        for i, d in enumerate(devs):
            out.append((i, f"{i}: {d['name']} (in={d['max_input_channels']}, out={d['max_output_channels']})"))
        return out

    def _parse_idx(self, s: str):
        if not s:
            return None
        try:
            return int(s.split(":",1)[0].strip())
        except Exception:
            return None

    def _build_audio(self):
        frm = self.tab_audio
        frm.columnconfigure(1, weight=1)

        devs = self._devices()
        names = [n for _, n in devs]

        ttk.Label(frm, text="Micrófono (tu voz):").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.mic_var = tk.StringVar(value=names[self.cfg.mic_device] if self.cfg.mic_device is not None and self.cfg.mic_device < len(names) else "")
        ttk.Combobox(frm, values=names, textvariable=self.mic_var).grid(row=0, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frm, text="Loopback (audio Teams/sistema):").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.loop_var = tk.StringVar(value=names[self.cfg.loopback_device] if self.cfg.loopback_device is not None and self.cfg.loopback_device < len(names) else "")
        ttk.Combobox(frm, values=names, textvariable=self.loop_var).grid(row=1, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frm, text="ASR model (CPU):").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.asr_var = tk.StringVar(value=self.cfg.asr_model_size)
        ttk.Combobox(frm, values=["tiny.en", "base.en"], textvariable=self.asr_var, width=20)            .grid(row=2, column=1, sticky="w", padx=10, pady=8)

        ttk.Label(frm, text="Sample rate:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.sr_var = tk.IntVar(value=self.cfg.sample_rate)
        ttk.Entry(frm, textvariable=self.sr_var, width=12).grid(row=3, column=1, sticky="w", padx=10, pady=8)

        hint = (
            "Selecciona como loopback el dispositivo de SALIDA (audífonos/altavoces) donde escuchas Teams.
"
            "El sistema usa WASAPI loopback. Si falla, prueba Stereo Mix o VB‑Cable."
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=10)

    def _build_context(self):
        frm = self.tab_context
        frm.columnconfigure(0, weight=1)

        ttk.Label(frm, text="Quién eres (perfil):").pack(anchor="w", padx=10, pady=(10, 4))
        self.profile_txt = tk.Text(frm, height=8)
        self.profile_txt.pack(fill="x", padx=10)
        self.profile_txt.insert("1.0", self.cfg.profile_context)

        ttk.Label(frm, text="Objetivo/tema de esta conversación:").pack(anchor="w", padx=10, pady=(10, 4))
        self.goal_txt = tk.Text(frm, height=5)
        self.goal_txt.pack(fill="x", padx=10)
        self.goal_txt.insert("1.0", self.cfg.goal_context)

    def _build_features(self):
        frm = self.tab_features
        frm.columnconfigure(1, weight=1)

        self.tr_var = tk.BooleanVar(value=self.cfg.enable_translation)
        ttk.Checkbutton(frm, text="Traducción EN→ES (lo que dice ella)", variable=self.tr_var)            .grid(row=0, column=0, sticky="w", padx=10, pady=8)

        self.doc_var = tk.BooleanVar(value=self.cfg.enable_document)
        ttk.Checkbutton(frm, text="Usar PDF como fuente (RAG)", variable=self.doc_var)            .grid(row=1, column=0, sticky="w", padx=10, pady=8)

        self.cite_var = tk.BooleanVar(value=self.cfg.cite_document)
        ttk.Checkbutton(frm, text="Citar página del PDF en overlay", variable=self.cite_var)            .grid(row=2, column=0, sticky="w", padx=10, pady=8)

        ttk.Label(frm, text="PDF:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.pdf_var = tk.StringVar(value=self.cfg.pdf_path)
        ttk.Entry(frm, textvariable=self.pdf_var).grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frm, text="Cargar…", command=self.pick_pdf).grid(row=3, column=2, padx=10, pady=8)

        ttk.Separator(frm).grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        ttk.Label(frm, text="LLM GGUF (opcional):").grid(row=5, column=0, sticky="w", padx=10, pady=8)
        self.llm_var = tk.StringVar(value=self.cfg.llm_model_path)
        ttk.Entry(frm, textvariable=self.llm_var).grid(row=5, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frm, text="Elegir…", command=self.pick_llm).grid(row=5, column=2, padx=10, pady=8)

        ttk.Separator(frm).grid(row=6, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        self.alpha_var = tk.DoubleVar(value=self.cfg.overlay_alpha)
        ttk.Label(frm, text="Opacidad overlay:").grid(row=7, column=0, sticky="w", padx=10, pady=8)
        ttk.Scale(frm, from_=0.12, to=0.95, variable=self.alpha_var, orient="horizontal")            .grid(row=7, column=1, sticky="ew", padx=10, pady=8)

        self.font_var = tk.IntVar(value=self.cfg.overlay_font_size)
        ttk.Label(frm, text="Tamaño letra:").grid(row=8, column=0, sticky="w", padx=10, pady=8)
        ttk.Spinbox(frm, from_=12, to=38, textvariable=self.font_var, width=8)            .grid(row=8, column=1, sticky="w", padx=10, pady=8)

        pos = ttk.Frame(frm)
        pos.grid(row=9, column=0, columnspan=3, sticky="w", padx=10, pady=8)
        self.posx_var = tk.IntVar(value=self.cfg.overlay_pos_x)
        self.posy_var = tk.IntVar(value=self.cfg.overlay_pos_y)
        ttk.Label(pos, text="Pos X:").pack(side="left")
        ttk.Entry(pos, textvariable=self.posx_var, width=6).pack(side="left", padx=6)
        ttk.Label(pos, text="Pos Y:").pack(side="left")
        ttk.Entry(pos, textvariable=self.posy_var, width=6).pack(side="left", padx=6)

        self.ct_var = tk.BooleanVar(value=self.cfg.overlay_click_through)
        ttk.Checkbutton(frm, text="Overlay click‑through (no estorba el mouse)", variable=self.ct_var)            .grid(row=10, column=0, sticky="w", padx=10, pady=8)

    def pick_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_var.set(path)

    def pick_llm(self):
        path = filedialog.askopenfilename(filetypes=[("GGUF model", "*.gguf")])
        if path:
            self.llm_var.set(path)

    def apply(self):
        self.cfg.mic_device = self._parse_idx(self.mic_var.get())
        self.cfg.loopback_device = self._parse_idx(self.loop_var.get())
        self.cfg.asr_model_size = self.asr_var.get().strip()
        self.cfg.sample_rate = int(self.sr_var.get())

        self.cfg.profile_context = self.profile_txt.get("1.0", "end").strip()
        self.cfg.goal_context = self.goal_txt.get("1.0", "end").strip()

        self.cfg.enable_translation = bool(self.tr_var.get())
        self.cfg.enable_document = bool(self.doc_var.get())
        self.cfg.cite_document = bool(self.cite_var.get())

        self.cfg.pdf_path = self.pdf_var.get().strip()
        self.cfg.llm_model_path = self.llm_var.get().strip()

        self.cfg.overlay_alpha = float(self.alpha_var.get())
        self.cfg.overlay_font_size = int(self.font_var.get())
        self.cfg.overlay_pos_x = int(self.posx_var.get())
        self.cfg.overlay_pos_y = int(self.posy_var.get())
        self.cfg.overlay_click_through = bool(self.ct_var.get())

        save_config(self.cfg)
        self.on_apply()
