# 🧪 Cómo Ejecutar Tests de Rendimiento Reales

## 📋 Resumen Rápido

```bash
# 1. Instalar dependencias (si no están instaladas)
pip install -r requirements.txt

# 2. Descargar modelos (REQUIERE INTERNET)
python3 download_models.py

# 3. Ejecutar tests reales
python3 test_real_performance.py
```

---

## 🎯 Tests Disponibles

### 1. `test_setup_and_config.py` - Verificación de Configuración
**No requiere modelos descargados** ✅

```bash
python3 test_setup_and_config.py
```

**Qué hace:**
- ✅ Verifica que todas las dependencias estén instaladas
- ✅ Detecta si los modelos están en cache
- ✅ Mide el overhead del sistema (VAD, conversión, etc.)
- ✅ Proporciona instrucciones de descarga

**Salida esperada:**
```
✅ Todas las dependencias están instaladas correctamente
📊 Overhead del Sistema: ~0.2ms (MÍNIMO)
⚠️ Modelos no disponibles en cache
```

---

### 2. `download_models.py` - Descarga de Modelos
**REQUIERE INTERNET** 🌐

```bash
python3 download_models.py
```

**Qué hace:**
- 📥 Descarga Qwen 0.5B Q4_K_M (~300MB)
- 📥 Descarga Whisper tiny.en (~75MB)
- 💾 Guarda en cache de HuggingFace

**Tiempo estimado:**
- Con internet rápido: 1-3 minutos
- Con internet normal: 3-10 minutos
- Con internet lento: 10-20 minutos

**Dónde se guardan:**
```
~/.cache/huggingface/hub/
├── models--Qwen--Qwen2.5-0.5B-Instruct-GGUF/
└── models--Systran--faster-whisper-tiny.en/
```

---

### 3. `test_real_performance.py` - Tests de Velocidad Real
**REQUIERE MODELOS DESCARGADOS** 📦

```bash
python3 test_real_performance.py
```

**Qué hace:**
- 🧪 Test 1: LLM (Qwen 0.5B)
  - Carga el modelo desde cache
  - Genera 3 respuestas de prueba
  - Mide latencia promedio, mínima y máxima
  
- 🧪 Test 2: ASR (Whisper tiny.en)
  - Carga el modelo desde cache
  - Transcribe 4 chunks de audio sintético
  - Mide RTF (Real-Time Factor)
  - Calcula latencias
  
- 🧪 Test 3: Pipeline Completo
  - Simula conversación real
  - Audio → ASR → LLM
  - Mide tiempo total del pipeline

**Salida esperada:**
```
✅ LLM (Qwen 0.5B):
   • Descarga: 2.5s (desde cache)
   • Latencia promedio: 350ms

✅ ASR (Whisper tiny.en):
   • Descarga: 1.8s (desde cache)
   • RTF: 0.18x
   • Latencia promedio: 180ms

✅ Pipeline Completo:
   • Tiempo total: 530ms
   • RTF: 0.21x
```

---

## 🚫 Limitaciones en CI/CD

### ¿Por qué no funcionan en GitHub Actions?

GitHub Actions **no tiene acceso a internet externo** para descargar desde HuggingFace.

**Error típico:**
```
❌ Error: [Errno -5] No address associated with hostname
```

### Soluciones:

#### Opción 1: Ejecutar Localmente (Recomendado) ✅
```bash
# En tu máquina local con internet:
git clone <repo>
cd copiloto-conversacional-ingles-fluido
pip install -r requirements.txt
python3 download_models.py
python3 test_real_performance.py
```

#### Opción 2: Docker con Modelos Pre-descargados
```dockerfile
FROM python:3.12

# Instalar dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Descargar modelos durante build
RUN python3 download_models.py

# Copiar código
COPY . /app
WORKDIR /app

# Ejecutar tests
CMD ["python3", "test_real_performance.py"]
```

#### Opción 3: GitHub Actions con Cache
```yaml
- name: Cache models
  uses: actions/cache@v3
  with:
    path: ~/.cache/huggingface
    key: models-${{ runner.os }}

- name: Download models (if not cached)
  run: python3 download_models.py

- name: Run performance tests
  run: python3 test_real_performance.py
```

---

## 📊 Resultados Esperados

### ASR (Whisper tiny.en + int8)
```
RTF (Real-Time Factor): 0.10-0.25x
Latencia: 100-250ms por segundo de audio
Estado: 🚀 EXCELENTE
```

**Interpretación:**
- RTF 0.20x significa que 1 segundo de audio se procesa en 200ms
- RTF < 1.0 = Viable para tiempo real
- RTF < 0.5 = Excelente para tiempo real
- RTF < 0.3 = Óptimo

### LLM (Qwen 0.5B Q4_K_M)
```
Latencia: 200-500ms por generación
Tokens: ~40-60 tokens por generación
Estado: ✅ BUENO
```

### Pipeline Completo (ASR + LLM)
```
Tiempo total: 300-750ms
RTF: 0.15-0.40x
Estado: ✅ BUENO para conversación en tiempo real
```

---

## 🔍 Verificar Modelos Descargados

```bash
# Ver modelos en cache
ls -lh ~/.cache/huggingface/hub/

# Ver tamaño total
du -sh ~/.cache/huggingface/hub/

# Limpiar cache (si necesitas espacio)
rm -rf ~/.cache/huggingface/hub/
```

---

## ❓ FAQ

### ¿Necesito GPU?
**No**. El sistema está optimizado para CPU:
- ASR: tiny.en es suficientemente rápido en CPU
- LLM: Qwen 0.5B Q4_K_M está cuantizado para CPU

Con GPU sería 5-10x más rápido, pero no es necesario.

### ¿Cuánto espacio ocupan los modelos?
```
LLM (Qwen 0.5B Q4_K_M): ~300MB
ASR (Whisper tiny.en): ~75MB
Total: ~375MB
```

### ¿Los modelos se descargan cada vez?
**No**. Se descargan **solo la primera vez**. Después se usan desde cache.

### ¿Puedo usar otros modelos?
Sí, pero los benchmarks cambiarán:
- `base.en` es más lento (RTF ~0.5x)
- `small.en` es muy lento (RTF ~1.0x)
- `tiny.en` es el más rápido para tiempo real

### ¿Funciona offline después de descargar?
**Sí**. Una vez descargados, los modelos están en cache y funcionan offline.

---

## 🎓 Entender los Resultados

### RTF (Real-Time Factor)
```
RTF = Tiempo de procesamiento / Duración del audio

Ejemplo:
  Audio: 1.0 segundo
  Procesamiento: 0.2 segundos
  RTF = 0.2 / 1.0 = 0.2x

✅ RTF < 1.0 → Más rápido que tiempo real
❌ RTF > 1.0 → Más lento que tiempo real
```

### Latencia
```
Tiempo desde que llega el audio hasta que sale la respuesta

Para conversación natural:
  • < 500ms → Excelente
  • < 1000ms → Bueno
  • < 2000ms → Aceptable
  • > 2000ms → Lento
```

---

## 📚 Documentos Relacionados

- `ANALISIS_VELOCIDAD_ASR.md` - Análisis técnico completo
- `TESTS_REALES_EXPLICACION.md` - Explicación detallada
- `RESUMEN_EJECUTIVO.md` - Resumen ejecutivo
- `verify_asr_config.py` - Verificación de optimizaciones

---

## ✅ Checklist para Tests Reales

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Verificar instalación: `python3 test_setup_and_config.py`
- [ ] Tener internet disponible
- [ ] Descargar modelos: `python3 download_models.py`
- [ ] Ejecutar tests: `python3 test_real_performance.py`
- [ ] Revisar resultados
- [ ] Comparar con benchmarks teóricos

---

*Última actualización*: 2026-02-03  
*Estado*: ✅ Scripts listos para ejecutar  
*Requisito*: Internet para primera descarga
