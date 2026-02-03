from typing import Dict, Any, List, Tuple, Optional

from app.coach.embedder import Embedder
from app.coach.translator import TranslatorENES
from app.rag.pdf_store import DocumentStore
from app.llm.llm_engine import LLMEngine

class Coach:
    def __init__(self,
                 profile_context: str,
                 goal_context: str,
                 enable_translation: bool,
                 enable_document: bool,
                 cite_document: bool,
                 llm: LLMEngine,
                 embedder: Embedder,
                 docstore: DocumentStore,
                 translator: TranslatorENES):
        self.profile_context = profile_context
        self.goal_context = goal_context

        self.enable_translation = enable_translation
        self.enable_document = enable_document
        self.cite_document = cite_document

        self.llm = llm
        self.embedder = embedder
        self.docstore = docstore
        self.translator = translator

        self.history: List[Tuple[str, str]] = []  # (speaker, text)
        self.topic_vec: Optional[object] = None

        self.last_suggest: Dict[str, Any] = {}
        self.last_her_text = ""

    def _update_topic(self, text: str):
        v = self.embedder.encode(text)
        if v is not None:
            self.topic_vec = v

    def _topic_shift(self, me_text: str) -> bool:
        # Use embeddings for topic shift detection
        if self.topic_vec is None or self.embedder.model is None:
            return False
        a = self.embedder.encode(me_text)
        if a is None:
            return False
        sim = self.embedder.cosine(a, self.topic_vec)
        return sim < 0.45

    def _system_prompt(self) -> str:
        return (
            "You are a real-time conversation copilot. Output STRICT JSON only.\n"
            "Max 2 sentences in say_now.\n"
            "Return JSON keys: say_now, intent, must_include (array), bridge_now (optional).\n"
        )

    def _build_user_prompt(self, her_text: str, me_partial: str = "", doc_ctx: str = "") -> str:
        hist = "\n".join([f"{spk.upper()}: {txt}" for spk, txt in self.history[-6:]])
        doc_part = f"\nDOCUMENT_CONTEXT:\n{doc_ctx}\n" if doc_ctx else ""
        return (
            f"PROFILE:\n{self.profile_context}\n\n"
            f"GOAL:\n{self.goal_context}\n\n"
            f"RECENT:\n{hist}\n\n"
            f"HER_LATEST:\n{her_text}\n\n"
            f"MY_PARTIAL:\n{me_partial}\n"
            f"{doc_part}\n"
            f"Write only JSON."
        )

    def maybe_translate_her(self, text: str) -> str:
        if not self.enable_translation:
            return ""
        return self.translator.translate(text)

    def _maybe_retrieve_doc(self, query: str) -> str:
        if not self.enable_document or not self.docstore.chunks:
            return ""
        hits = self.docstore.retrieve(query, k=3)
        if not hits:
            return ""
        # small snippets only
        parts = []
        for chunk, page, _score in hits:
            snippet = chunk[:600]
            if self.cite_document:
                parts.append(f"(p.{page}) {snippet}")
            else:
                parts.append(snippet)
        return "\n".join(parts)

    def suggest_draft(self, her_partial: str) -> Dict[str, Any]:
        if not her_partial.strip():
            return {}
        
        doc_ctx = self._maybe_retrieve_doc(her_partial)
        
        # Always use LLM, no fallback templates
        out = self.llm.generate_json(self._system_prompt(), self._build_user_prompt(her_partial, "", doc_ctx), max_tokens=70)
        return out

    def suggest_final(self, her_final: str) -> Dict[str, Any]:
        if not her_final.strip():
            return {}
        self.last_her_text = her_final
        self.history.append(("her", her_final))
        self._update_topic(her_final)

        doc_ctx = self._maybe_retrieve_doc(her_final)

        # Always use LLM, no fallback templates
        out = self.llm.generate_json(self._system_prompt(), self._build_user_prompt(her_final, "", doc_ctx), max_tokens=90)
        self.last_suggest = out
        return out

    def evaluate_me(self, me_final: str) -> Dict[str, Any]:
        if not me_final.strip():
            return {}
        self.history.append(("me", me_final))

        status = "ok"
        notes = []

        if self._topic_shift(me_final):
            status = "topic_shift"
            notes.append("Topic shift detected.")

        # slot check
        missing = []
        for s in (self.last_suggest.get("must_include") or []):
            if isinstance(s, str) and s and s.lower() not in me_final.lower():
                missing.append(s)
        if missing:
            status = "missing_slots"
            notes.append("Missing: " + ", ".join(missing))

        # provide bridge suggestion using LLM if topic shift
        suggest = {}
        if status == "topic_shift":
            # Use LLM to generate bridge suggestion
            bridge_prompt = f"Generate a brief bridge phrase to transition from '{self.last_her_text}' to a new topic. Return JSON with bridge_now and say_now keys."
            bridge_response = self.llm.generate_json(self._system_prompt(), bridge_prompt, max_tokens=60)
            if bridge_response:
                suggest = bridge_response

        return {"status": status, "notes": notes, "suggest": suggest}
