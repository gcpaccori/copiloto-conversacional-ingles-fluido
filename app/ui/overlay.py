import tkinter as tk
from app.ui.win_clickthrough import set_clickthrough

class OverlayUI:
    def __init__(self, root: tk.Tk):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")

        self.label = tk.Label(
            self.win,
            text="",
            fg="white",
            bg="black",
            justify="left",
            font=("Segoe UI", 18, "bold"),
            wraplength=520
        )
        self.label.pack(padx=10, pady=8)

        self._clickthrough_enabled = False
        self.visible = True

    def apply_style(self, alpha: float, font_size: int, x: int, y: int, clickthrough: bool):
        self.win.attributes("-alpha", max(0.12, min(0.95, alpha)))
        self.label.config(font=("Segoe UI", font_size, "bold"))
        self.win.geometry(f"+{x}+{y}")
        self.set_clickthrough(clickthrough)

    def set_text(self, text: str):
        self.label.config(text=text)

    def set_clickthrough(self, enabled: bool):
        try:
            hwnd = self.win.winfo_id()
            set_clickthrough(hwnd, enabled)
            self._clickthrough_enabled = enabled
        except Exception:
            self._clickthrough_enabled = False

    def toggle_clickthrough(self):
        self.set_clickthrough(not self._clickthrough_enabled)

    def toggle_visible(self):
        if self.visible:
            self.win.withdraw()
            self.visible = False
        else:
            self.win.deiconify()
            self.visible = True

    def set_topmost(self, enabled: bool):
        self.win.attributes("-topmost", bool(enabled))
