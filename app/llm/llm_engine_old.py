import json
import os
from typing import Dict, Any

try:
    from llama_cpp import Llama
except Exception:
    Llama = None

def safe_json_extract(text: str) -> Dict[str, Any]:
    text = text.strip()
    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(text[i:j+1])
        except Exception:
            return {}
    return {}

class LLMEngine:
    def __init__(self, model_path: str, n_ctx: int, n_threads: int):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.llm = None
        self.ready = False
        self._init()

    def _init(self):
        if not self.model_path:
            return
        if not os.path.exists(self.model_path):
            return
        if Llama is None:
            return
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=0,
                verbose=False
            )
            self.ready = True
        except Exception:
            self.ready = False
            self.llm = None

    def generate_json(self, system: str, user: str, max_tokens: int = 90) -> Dict[str, Any]:
        if not self.ready or self.llm is None:
            return {}
        prompt = f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"
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
