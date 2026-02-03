\
# Copiloto conversacional (PC) — MVP

Este mini‑repo crea un **copiloto conversacional en tiempo real** para PC (Windows), pensado para:
- Ella por **Microsoft Teams/Meetings** (audio del sistema / loopback).
- Tú por **micrófono**.
- ASR en vivo (inglés) + sugerencias "SAY NOW".
- Evaluación de tu respuesta vs sugerencia.
- Traducción opcional EN→ES (lo que dice ella).
- PDF opcional como fuente (RAG) activable/desactivable.
- Overlay **casi invisible** + ventana de configuración visible.
- Overlay **click‑through** (no estorba el mouse).

> Nota: Capturar audio del sistema depende de WASAPI loopback. Si tu PC no lo permite, usa "Stereo Mix" o un driver virtual (VB‑Cable).

## 1) Instalación rápida (PowerShell)
```powershell
cd .\copiloto_pc
.\scripts\setup.ps1
```

Esto crea `.\.venv`, instala dependencias base y deja un comando para correr.

## 2) Ejecutar
```powershell
.\scripts\run.ps1
```

Se abre la ventana de configuración:
1) Elige tu **Micrófono** (tu voz).
2) Elige **Loopback**: el dispositivo de salida donde escuchas Teams (audífonos/altavoces).
3) ASR model: empieza con `tiny.en`.
4) Guarda y aplica.

## 3) Modelos
### ASR (Whisper)
`faster-whisper` descargará el modelo la primera vez (requiere internet) a menos que lo caches.

### LLM (REQUERIDO - Qwen 0.5B)
Este proyecto requiere Qwen 0.5B Instruct en formato GGUF. 
- Descarga el modelo desde Hugging Face: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
- Elige una variante (recomendado: `qwen2.5-0.5b-instruct-q4_k_m.gguf` para balance entre velocidad y calidad)
- Configura la ruta en Configuración → Funciones → LLM
- El sistema NO usa plantillas hardcodeadas ni lógica if-else, todo es generado por el LLM

## 4) Atajos
- **F8**: toggle click-through (si quieres interactuar con el overlay).
- **F9**: mostrar/ocultar overlay.
- **F10**: fijar overlay encima (topmost).

(Estos atajos solo usan Tkinter; si no funcionan en tu Windows, puedes moverlos a botones.)

## 5) Estructura
- `app/main.py` — orquestador
- `app/ui/*` — overlay + config
- `app/audio/*` — captura + VAD/segmentos
- `app/asr/*` — faster-whisper
- `app/coach/*` — lógica de sugerencias + evaluación
- `app/rag/*` — PDF chunking + búsqueda
- `scripts/*` — setup / run
