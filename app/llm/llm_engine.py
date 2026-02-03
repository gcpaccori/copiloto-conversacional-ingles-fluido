import json
import os
from typing import Dict, Any

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    Llama = None
    LLAMA_CPP_AVAILABLE = False

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
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python is required. Install with: pip install llama-cpp-python>=0.2.90")
        
        if not self.model_path:
            raise ValueError("LLM model path is required. Please configure llm_model_path in config.")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"LLM model not found at: {self.model_path}")
        
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=0,
                verbose=False
            )
            self.ready = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM: {e}")

    def generate_json(self, system: str, user: str, max_tokens: int = 90) -> Dict[str, Any]:
        if not self.ready or self.llm is None:
            raise RuntimeError("LLM is not ready. Ensure model is properly loaded.")
        
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
        except Exception as e:
            raise RuntimeError(f"Error generating response: {e}")
