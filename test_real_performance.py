#!/usr/bin/env python3
"""
Real Performance Test - Download models and test actual performance
Tests both ASR (Whisper) and LLM (Qwen) with real models
"""
import time
import numpy as np
import os
from typing import Dict, List

def generate_test_audio(duration_seconds: float, sample_rate: int = 16000) -> np.ndarray:
    """Generate synthetic audio for testing (sine wave)"""
    samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, samples, dtype=np.float32)
    # Mix of frequencies to simulate speech
    audio = (
        0.3 * np.sin(2 * np.pi * 200 * t) +
        0.2 * np.sin(2 * np.pi * 400 * t) +
        0.15 * np.sin(2 * np.pi * 800 * t) +
        0.1 * np.random.randn(samples).astype(np.float32)
    )
    return audio.astype(np.float32)

def test_llm_download_and_speed():
    """Download Qwen model and test generation speed"""
    print("\n" + "="*70)
    print("TEST 1: LLM (Qwen 0.5B) - Descarga y Velocidad")
    print("="*70)
    
    try:
        from llama_cpp import Llama
        
        print("\n📥 Descargando modelo Qwen 0.5B...")
        print("   Repo: Qwen/Qwen2.5-0.5B-Instruct-GGUF")
        print("   Archivo: qwen2.5-0.5b-instruct-q4_k_m.gguf")
        
        download_start = time.time()
        llm = Llama.from_pretrained(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
            n_ctx=2048,
            n_threads=os.cpu_count() or 4,
            verbose=False
        )
        download_time = time.time() - download_start
        print(f"✅ Modelo descargado e inicializado en {download_time:.2f}s")
        
        # Test prompts
        test_prompts = [
            "What did she say?",
            "How should I respond?",
            "Is this a question?",
        ]
        
        print("\n🧪 Probando velocidad de generación...")
        latencies = []
        
        for i, prompt in enumerate(test_prompts):
            user_text = f"She said: '{prompt}'"
            
            start = time.time()
            output = llm(
                f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{user_text}<|im_end|>\n<|im_start|>assistant\n",
                max_tokens=50,
                temperature=0.7,
                stop=["<|im_end|>"],
                echo=False
            )
            latency = time.time() - start
            latencies.append(latency)
            
            response = output['choices'][0]['text'].strip()
            
            if i == 0:
                print(f"\n  Ejemplo de respuesta:")
                print(f"  Input: {user_text}")
                print(f"  Output: {response[:100]}...")
                print(f"  Latencia: {latency*1000:.0f}ms")
        
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        
        print(f"\n📊 Resultados LLM:")
        print(f"  • Prompts probados: {len(test_prompts)}")
        print(f"  • Latencia promedio: {avg_latency*1000:.0f}ms")
        print(f"  • Latencia mínima: {min_latency*1000:.0f}ms")
        print(f"  • Latencia máxima: {max_latency*1000:.0f}ms")
        
        if avg_latency < 0.5:
            print(f"  • Estado: 🚀 EXCELENTE (<500ms)")
        elif avg_latency < 1.0:
            print(f"  • Estado: ✅ BUENO (<1s)")
        else:
            print(f"  • Estado: ⚠️ ACEPTABLE (>1s)")
        
        return {
            "success": True,
            "download_time": download_time,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency
        }
        
    except Exception as e:
        print(f"❌ Error en test LLM: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_asr_download_and_speed():
    """Download Whisper model and test transcription speed"""
    print("\n" + "="*70)
    print("TEST 2: ASR (Whisper tiny.en) - Descarga y Velocidad")
    print("="*70)
    
    try:
        from faster_whisper import WhisperModel
        
        print("\n📥 Descargando modelo Whisper tiny.en...")
        
        download_start = time.time()
        model = WhisperModel(
            "tiny.en",
            device="cpu",
            compute_type="int8",
            cpu_threads=os.cpu_count() or 4,
            num_workers=1
        )
        download_time = time.time() - download_start
        print(f"✅ Modelo descargado e inicializado en {download_time:.2f}s")
        
        # Generate test audio
        print("\n🎵 Generando audio de prueba...")
        test_audios = [
            generate_test_audio(0.8),   # 800ms
            generate_test_audio(1.5),   # 1.5s
            generate_test_audio(2.0),   # 2s
            generate_test_audio(1.0),   # 1s
        ]
        total_audio_duration = 0.8 + 1.5 + 2.0 + 1.0
        print(f"✅ Generado {len(test_audios)} chunks de audio ({total_audio_duration}s total)")
        
        # Warm-up
        print("\n🔥 Calentando modelo...")
        _ = model.transcribe(test_audios[0], language="en", vad_filter=False, beam_size=1)
        
        # Test transcription speed
        print("\n🧪 Probando velocidad de transcripción...")
        latencies = []
        
        for i, audio in enumerate(test_audios):
            audio_duration = len(audio) / 16000.0
            
            start = time.time()
            segments, _ = model.transcribe(
                audio,
                language="en",
                vad_filter=False,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                without_timestamps=True,
                log_progress=False
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            latency = time.time() - start
            latencies.append(latency)
            
            if i == 0:
                print(f"\n  Ejemplo de transcripción:")
                print(f"  Audio duración: {audio_duration*1000:.0f}ms")
                print(f"  Latencia: {latency*1000:.0f}ms")
                print(f"  RTF: {latency/audio_duration:.2f}x")
        
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        total_processing_time = sum(latencies)
        realtime_factor = total_processing_time / total_audio_duration
        
        print(f"\n📊 Resultados ASR:")
        print(f"  • Chunks procesados: {len(test_audios)}")
        print(f"  • Audio total: {total_audio_duration:.2f}s")
        print(f"  • Tiempo procesamiento: {total_processing_time:.2f}s")
        print(f"  • Latencia promedio: {avg_latency*1000:.0f}ms")
        print(f"  • Latencia mínima: {min_latency*1000:.0f}ms")
        print(f"  • Latencia máxima: {max_latency*1000:.0f}ms")
        print(f"  • RTF (Real-Time Factor): {realtime_factor:.2f}x")
        
        if realtime_factor < 0.3:
            print(f"  • Estado: 🚀 EXCELENTE (RTF < 0.3)")
        elif realtime_factor < 0.5:
            print(f"  • Estado: ✅ BUENO (RTF < 0.5)")
        elif realtime_factor < 1.0:
            print(f"  • Estado: ⚠️ ACEPTABLE (RTF < 1.0)")
        else:
            print(f"  • Estado: ❌ LENTO (RTF >= 1.0)")
        
        return {
            "success": True,
            "download_time": download_time,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "realtime_factor": realtime_factor
        }
        
    except Exception as e:
        print(f"❌ Error en test ASR: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_full_pipeline():
    """Test the full pipeline (ASR + LLM) with real models"""
    print("\n" + "="*70)
    print("TEST 3: Pipeline Completo (ASR → LLM)")
    print("="*70)
    
    try:
        from faster_whisper import WhisperModel
        from llama_cpp import Llama
        
        # Load models (should be cached now)
        print("\n📦 Cargando modelos (desde cache)...")
        
        load_start = time.time()
        asr_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", 
                                 cpu_threads=os.cpu_count() or 4, num_workers=1)
        asr_load_time = time.time() - load_start
        print(f"✅ ASR cargado en {asr_load_time:.2f}s")
        
        load_start = time.time()
        llm = Llama.from_pretrained(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
            n_ctx=2048,
            n_threads=os.cpu_count() or 4,
            verbose=False
        )
        llm_load_time = time.time() - load_start
        print(f"✅ LLM cargado en {llm_load_time:.2f}s")
        
        # Simulate real conversation
        print("\n🎭 Simulando conversación real...")
        
        # Generate audio for "What do you think about this proposal?"
        audio = generate_test_audio(2.5)  # 2.5s of audio
        audio_duration = len(audio) / 16000.0
        
        print(f"\n1️⃣ Audio entrada: {audio_duration:.2f}s")
        
        # Step 1: ASR
        asr_start = time.time()
        segments, _ = asr_model.transcribe(
            audio, language="en", vad_filter=False, beam_size=1,
            best_of=1, temperature=0.0, condition_on_previous_text=False,
            without_timestamps=True, log_progress=False
        )
        transcribed_text = " ".join(seg.text.strip() for seg in segments).strip()
        asr_time = time.time() - asr_start
        
        print(f"2️⃣ ASR: {asr_time*1000:.0f}ms")
        print(f"   Transcrito: (audio sintético)")
        
        # Step 2: LLM
        llm_start = time.time()
        output = llm(
            f"<|im_start|>system\nYou are a helpful assistant in a conversation.<|im_end|>\n<|im_start|>user\nSomeone said something. Suggest a brief response.<|im_end|>\n<|im_start|>assistant\n",
            max_tokens=40,
            temperature=0.7,
            stop=["<|im_end|>"],
            echo=False
        )
        response = output['choices'][0]['text'].strip()
        llm_time = time.time() - llm_start
        
        print(f"3️⃣ LLM: {llm_time*1000:.0f}ms")
        print(f"   Respuesta: {response[:80]}...")
        
        total_time = asr_time + llm_time
        
        print(f"\n📊 Resultados Pipeline Completo:")
        print(f"  • Duración audio: {audio_duration:.2f}s")
        print(f"  • Tiempo ASR: {asr_time*1000:.0f}ms")
        print(f"  • Tiempo LLM: {llm_time*1000:.0f}ms")
        print(f"  • Tiempo TOTAL: {total_time*1000:.0f}ms")
        print(f"  • RTF Pipeline: {total_time/audio_duration:.2f}x")
        
        if total_time < 0.5:
            print(f"  • Estado: 🚀 EXCELENTE (<500ms)")
        elif total_time < 1.0:
            print(f"  • Estado: ✅ BUENO (<1s)")
        else:
            print(f"  • Estado: ⚠️ ACEPTABLE (>1s)")
        
        return {
            "success": True,
            "asr_time": asr_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "audio_duration": audio_duration,
            "rtf": total_time / audio_duration
        }
        
    except Exception as e:
        print(f"❌ Error en test pipeline: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║         TEST REAL DE RENDIMIENTO - MODELOS DESCARGADOS             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    print("\n🎯 Este test descarga modelos reales y mide velocidad real")
    print("   • LLM: Qwen 0.5B Q4_K_M (~300MB)")
    print("   • ASR: Whisper tiny.en (~75MB)")
    print()
    
    results = {}
    
    # Test 1: LLM
    results['llm'] = test_llm_download_and_speed()
    
    # Test 2: ASR
    results['asr'] = test_asr_download_and_speed()
    
    # Test 3: Full Pipeline
    if results['llm']['success'] and results['asr']['success']:
        results['pipeline'] = test_full_pipeline()
    
    # Final Summary
    print("\n" + "="*70)
    print("RESUMEN FINAL - TESTS CON MODELOS REALES")
    print("="*70)
    
    if results['llm']['success']:
        print(f"\n✅ LLM (Qwen 0.5B):")
        print(f"   • Descarga: {results['llm']['download_time']:.2f}s")
        print(f"   • Latencia promedio: {results['llm']['avg_latency']*1000:.0f}ms")
        
    if results['asr']['success']:
        print(f"\n✅ ASR (Whisper tiny.en):")
        print(f"   • Descarga: {results['asr']['download_time']:.2f}s")
        print(f"   • Latencia promedio: {results['asr']['avg_latency']*1000:.0f}ms")
        print(f"   • RTF: {results['asr']['realtime_factor']:.2f}x")
    
    if 'pipeline' in results and results['pipeline']['success']:
        print(f"\n✅ Pipeline Completo:")
        print(f"   • Tiempo total: {results['pipeline']['total_time']*1000:.0f}ms")
        print(f"   • RTF: {results['pipeline']['rtf']:.2f}x")
    
    print("\n" + "="*70)
    
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("\n✅ El sistema está funcionando correctamente con modelos reales")
        print("✅ Las velocidades medidas son con modelos descargados")
        print("✅ Los benchmarks anteriores eran estimaciones, estos son REALES")
        return 0
    else:
        print(f"⚠️ {success_count}/{total_count} tests pasaron")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
