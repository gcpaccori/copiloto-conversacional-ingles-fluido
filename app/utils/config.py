import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config.json")

@dataclass
class AppConfig:
    sample_rate: int = 16000
    mic_device: Optional[int] = None
    loopback_device: Optional[int] = None

    asr_model_size: str = "tiny.en"
    asr_compute_type: str = "int8"

    enable_translation: bool = False
    enable_document: bool = False
    cite_document: bool = True
    pdf_path: str = ""

    llm_model_path: str = ""
    llm_ctx: int = 2048
    llm_threads: int = 4

    overlay_alpha: float = 0.28
    overlay_font_size: int = 18
    overlay_pos_x: int = 80
    overlay_pos_y: int = 80
    overlay_click_through: bool = True

    profile_context: str = "My name is Gabriel. I work in IT / Cloud / IoT."
    goal_context: str = "Have a smooth professional conversation in English."

def load_config(default_path: str) -> AppConfig:
    # If config.json exists, load it. Otherwise copy default.
    cfg_path = os.path.abspath(CONFIG_PATH)
    if not os.path.exists(cfg_path):
        with open(default_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        save_config(AppConfig(**data))
        return AppConfig(**data)

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AppConfig(**data)

def save_config(cfg: AppConfig) -> None:
    cfg_path = os.path.abspath(CONFIG_PATH)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
