#!/usr/bin/env python3
"""
ASR Performance Test - Verify real-time audio processing speed
Tests different Whisper models and configurations for optimal speed
"""
import time
import numpy as np
from typing import List, Tuple, Dict

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

def test_model(model_size: str, compute_type: str, audio_chunks: List[np.ndarray]) -> Dict:
    """Test a specific model configuration"""
    from app.asr.whisper_asr import ASREngine
    
    print(f"\n{'='*70}")
    print(f"Testing: {model_size} with compute_type={compute_type}")
    print(f"{'='*70}")
    
    # Initialize model
    print(f"Initializing {model_size}...")
    init_start = time.time()
    asr = ASREngine(model_size=model_size, compute_type=compute_type)
    init_time = time.time() - init_start
    
    if not asr.ready:
        print(f"❌ Failed to initialize {model_size}")
        return {
            "model": model_size,
            "compute_type": compute_type,
            "status": "failed",
            "init_time": init_time,
            "avg_latency": None,
            "total_time": None,
            "realtime_factor": None
        }
    
    print(f"✓ Model loaded in {init_time:.2f}s")
    
    # Warm-up run (first run is often slower)
    print("Warming up...")
    _ = asr.transcribe(audio_chunks[0])
    
    # Test transcription speed
    print(f"Testing {len(audio_chunks)} audio chunks...")
    latencies = []
    total_audio_duration = 0
    
    for i, audio in enumerate(audio_chunks):
        audio_duration = len(audio) / 16000.0
        total_audio_duration += audio_duration
        
        start = time.time()
        text = asr.transcribe(audio)
        latency = time.time() - start
        latencies.append(latency)
        
        if i == 0:
            print(f"  First chunk: {latency*1000:.0f}ms (audio: {audio_duration*1000:.0f}ms)")
            print(f"  Transcription: '{text[:80]}...'")
    
    avg_latency = np.mean(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    total_processing_time = sum(latencies)
    realtime_factor = total_processing_time / total_audio_duration
    
    print(f"\n📊 Results:")
    print(f"  • Average latency: {avg_latency*1000:.0f}ms")
    print(f"  • Min latency: {min_latency*1000:.0f}ms")
    print(f"  • Max latency: {max_latency*1000:.0f}ms")
    print(f"  • Total audio duration: {total_audio_duration:.2f}s")
    print(f"  • Total processing time: {total_processing_time:.2f}s")
    print(f"  • Real-time factor: {realtime_factor:.2f}x")
    
    # Evaluate real-time capability
    if realtime_factor < 0.3:
        status = "🚀 EXCELLENT - Muy rápido para tiempo real"
    elif realtime_factor < 0.5:
        status = "✅ GOOD - Bueno para tiempo real"
    elif realtime_factor < 1.0:
        status = "⚠️ ACCEPTABLE - Aceptable para tiempo real"
    else:
        status = "❌ SLOW - Demasiado lento para tiempo real"
    
    print(f"  • Status: {status}")
    
    return {
        "model": model_size,
        "compute_type": compute_type,
        "status": status,
        "init_time": init_time,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "total_time": total_processing_time,
        "audio_duration": total_audio_duration,
        "realtime_factor": realtime_factor
    }

def main():
    print("="*70)
    print("ASR Performance Test - Real-time Audio Processing")
    print("="*70)
    print("\n🎯 Objetivo: Verificar velocidad para audio en tiempo real")
    print("   - Requerimiento: RTF (Real-Time Factor) < 1.0")
    print("   - Óptimo: RTF < 0.5 para respuesta fluida")
    print()
    
    # Generate test audio chunks (simulating real-time segments)
    print("Generating test audio...")
    audio_chunks = [
        generate_test_audio(0.8),  # 800ms partial
        generate_test_audio(1.5),  # 1.5s final
        generate_test_audio(0.8),  # 800ms partial
        generate_test_audio(2.0),  # 2s final
        generate_test_audio(1.0),  # 1s partial
        generate_test_audio(3.0),  # 3s final
    ]
    print(f"✓ Generated {len(audio_chunks)} test audio chunks")
    
    # Test configurations
    test_configs = [
        ("tiny.en", "int8"),
        ("tiny.en", "float32"),
        ("base.en", "int8"),
        ("base.en", "float32"),
    ]
    
    results = []
    
    for model_size, compute_type in test_configs:
        try:
            result = test_model(model_size, compute_type, audio_chunks)
            results.append(result)
        except Exception as e:
            print(f"❌ Error testing {model_size} with {compute_type}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)
    print()
    print(f"{'Model':<15} {'Compute':<10} {'Avg Latency':<15} {'RTF':<10} {'Status':<30}")
    print("-"*70)
    
    best_config = None
    best_rtf = float('inf')
    
    for r in results:
        if r.get('avg_latency') is not None:
            print(f"{r['model']:<15} {r['compute_type']:<10} {r['avg_latency']*1000:>7.0f}ms{'':<8} {r['realtime_factor']:>5.2f}x{'':<5} {r['status']}")
            if r['realtime_factor'] < best_rtf:
                best_rtf = r['realtime_factor']
                best_config = r
    
    print()
    print("="*70)
    print("RECOMENDACIÓN FINAL")
    print("="*70)
    
    if best_config:
        print(f"\n🏆 Mejor configuración: {best_config['model']} con {best_config['compute_type']}")
        print(f"   • Latencia promedio: {best_config['avg_latency']*1000:.0f}ms")
        print(f"   • Factor tiempo real: {best_config['realtime_factor']:.2f}x")
        print(f"   • Tiempo inicialización: {best_config['init_time']:.2f}s")
        
        if best_config['realtime_factor'] < 0.5:
            print(f"\n✅ El sistema PUEDE funcionar a buena velocidad en tiempo real")
            print(f"   La configuración actual con faster-whisper es ÓPTIMA")
            print(f"   No se requieren cambios adicionales")
        elif best_config['realtime_factor'] < 1.0:
            print(f"\n⚠️ El sistema puede funcionar pero con latencia perceptible")
            print(f"   Considerar usar GPU o modelo más pequeño")
        else:
            print(f"\n❌ El sistema es DEMASIADO LENTO para tiempo real")
            print(f"   Se requiere GPU o modelo más pequeño")
    
    print()
    print("📝 Notas:")
    print("   • faster-whisper es la implementación correcta para tiempo real")
    print("   • whisper.cpp sería alternativa pero requiere compilación")
    print("   • tiny.en es el modelo más rápido y adecuado para tiempo real")
    print("   • int8 da el mejor balance velocidad/calidad")
    print("   • GPU aceleraría 5-10x pero no es necesario con tiny.en")
    print()
    
    return 0 if best_config and best_config['realtime_factor'] < 1.0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
