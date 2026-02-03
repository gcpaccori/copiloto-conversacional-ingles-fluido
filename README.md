# Copiloto Conversacional en Inglés Fluido

Sistema de conversación en tiempo real con IA para practicar inglés, optimizado para CPU.

## 🎯 Características

- **ASR en Tiempo Real**: Transcripción de audio usando Whisper (faster-whisper)
- **LLM Local**: Sugerencias conversacionales con Qwen 0.5B
- **Optimizado para CPU**: No requiere GPU, funciona en hardware común
- **Doble Captura**: Micrófono (tu voz) + Loopback (audio del sistema)
- **Overlay Transparente**: Interfaz no intrusiva con sugerencias en pantalla

## 🚀 Instalación Rápida

### Requisitos
- Python 3.8+
- Windows 10/11 (para captura de audio WASAPI)
- 4GB RAM mínimo, 8GB recomendado
- CPU de 4 núcleos o más

### Instalación

```powershell
# Clonar repositorio
git clone https://github.com/gcpaccori/copiloto-conversacional-ingles-fluido.git
cd copiloto-conversacional-ingles-fluido

# Crear entorno virtual e instalar dependencias
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Modelos Requeridos

Los modelos se descargan automáticamente desde HuggingFace la primera vez:

**ASR (Whisper tiny.en)**
- Se descarga automáticamente de `Systran/faster-whisper-tiny.en`
- Tamaño: ~75MB

**LLM (Qwen 0.5B)**
- Se descarga automáticamente de `Qwen/Qwen2.5-0.5B-Instruct-GGUF`
- Archivo: `qwen2.5-0.5b-instruct-q4_k_m.gguf`
- Tamaño: ~491MB

## ▶️ Uso

```powershell
# Ejecutar la aplicación
python app/main.py
```

### Configuración Inicial

1. Selecciona tu **micrófono** (tu voz)
2. Selecciona **Loopback** (audio del sistema - Teams/Zoom/etc)
3. El sistema descargará los modelos automáticamente
4. ¡Listo para usar!

### Atajos de Teclado

- **F8**: Alternar click-through del overlay
- **F9**: Mostrar/ocultar overlay
- **F10**: Fijar overlay encima (topmost)

## 📊 Rendimiento

Sistema validado en CPU sin GPU. Ver [PERFORMANCE.md](PERFORMANCE.md) para resultados detallados.

**Velocidades Medidas (CPU AMD EPYC 7763, 4 cores):**
- ASR: ~316ms por transcripción (RTF 0.24x)
- LLM: ~294ms por respuesta
- Pipeline completo: ~924ms

✅ **Apto para conversaciones en tiempo real**

### 📋 Características Completas

Ver [FEATURES_ES.md](FEATURES_ES.md) para documentación completa en español sobre:
- ✅ Pruebas de rendimiento del flujo completo (audio → transcripción → respuesta)
- ✅ Manejo de preguntas largas y complejas (hasta 15+ segundos)
- ✅ Tiempos de respuesta verificados (< 2 segundos)
- ✅ Configuración de contexto inicial personalizado (profile + goal)
- ✅ Carga de documentos PDF (niveles de inglés, técnicas, vocabulario)
- ✅ Funcionalidad completa como copiloto conversacional

## 📁 Estructura del Proyecto

```
copiloto-conversacional-ingles-fluido/
├── app/
│   ├── main.py              # Punto de entrada
│   ├── audio/               # Captura y procesamiento de audio
│   ├── asr/                 # Motor de transcripción (Whisper)
│   ├── llm/                 # Motor LLM (Qwen)
│   ├── coach/               # Lógica de sugerencias
│   ├── ui/                  # Interfaz de usuario
│   └── utils/               # Utilidades
├── scripts/                 # Scripts de instalación
├── config.default.json      # Configuración por defecto
└── requirements.txt         # Dependencias Python
```

## 🔧 Configuración Avanzada

Edita `config.json` (se crea en primera ejecución) para ajustar:

```json
{
  "asr_model_size": "Systran/faster-whisper-tiny.en",
  "asr_compute_type": "int8",
  "llm_model_path": "",
  "sample_rate": 16000
}
```

## 🛠️ Desarrollo

### Instalar dependencias de desarrollo

```bash
pip install -r requirements-optional.txt
```

### Ejecutar tests

```bash
# Verificación rápida (sin descargar modelos)
python test_quick_verification.py

# Test de rendimiento completo (descarga modelos automáticamente)
python test_full_performance.py
```

Ver [TESTING.md](TESTING.md) para guía completa de testing.

## 📝 Notas Técnicas

- **ASR**: Usa `faster-whisper` con modelo `tiny.en` + cuantización INT8
- **LLM**: Usa `llama-cpp-python` con modelo Qwen Q4_K_M
- **VAD**: Usa `webrtcvad` para detección de voz
- **Audio**: Captura WASAPI en Windows

### Optimizaciones Implementadas

- Beam size = 1 (greedy decoding)
- Sin timestamps en transcripción
- Cuantización INT8 para ASR
- Cuantización Q4_K_M para LLM
- Threads automáticos según CPU

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:
1. Haz fork del repositorio
2. Crea una rama para tu feature
3. Haz commit de tus cambios
4. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT.

## 🙏 Créditos

- **Whisper**: OpenAI
- **faster-whisper**: SYSTRAN
- **Qwen**: Alibaba Cloud
- **llama-cpp-python**: Comunidad llama.cpp
