try:
    import argostranslate.translate
except Exception:
    argostranslate = None

class TranslatorENES:
    def __init__(self):
        self.ready = False
        try:
            # Will be True only if argostranslate installed and has language packages
            self.ready = True if argostranslate is not None else False
        except Exception:
            self.ready = False

    def translate(self, text: str) -> str:
        if not self.ready or argostranslate is None:
            return ""
        try:
            return argostranslate.translate.translate(text, "en", "es")
        except Exception:
            return ""
