import os
from typing import List, Tuple, Optional
import numpy as np

try:
    import fitz
except Exception:
    fitz = None

from app.coach.embedder import Embedder

class DocumentStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self.chunks: List[str] = []
        self.pages: List[int] = []
        self.vecs: Optional[np.ndarray] = None

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
            for part in self._chunk_text(text, chunk_chars=1400, overlap=200):
                chunks.append(part)
                pages.append(p + 1)

        self.chunks = chunks
        self.pages = pages

        if self.embedder.model is not None and self.chunks:
            vec_list = []
            for c in self.chunks:
                v = self.embedder.encode(c)
                if v is not None:
                    vec_list.append(v)
            self.vecs = np.stack(vec_list, axis=0) if vec_list else None
        else:
            self.vecs = None

        return True

    @staticmethod
    def _chunk_text(text: str, chunk_chars: int, overlap: int) -> List[str]:
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
        if not self.chunks:
            return []
        qv = self.embedder.encode(query) if self.embedder.model is not None else None

        if qv is not None and self.vecs is not None and self.vecs.shape[0] == len(self.chunks):
            sims = self.vecs @ qv
            idx = np.argsort(-sims)[:k]
            return [(self.chunks[int(i)], self.pages[int(i)], float(sims[int(i)])) for i in idx]

        q = query.lower()
        scored = []
        for c, p in zip(self.chunks, self.pages):
            score = sum(1 for w in q.split() if w in c.lower())
            scored.append((c, p, float(score)))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:k]
