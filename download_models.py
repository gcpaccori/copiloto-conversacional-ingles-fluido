#!/usr/bin/env python3
"""
Script para descargar modelos automáticamente
Ejecutar con: python3 download_models.py
"""

def download_llm():
    """Descarga el modelo LLM (Qwen 0.5B)"""
    print("="*70)
    print("Descargando LLM: Qwen 0.5B Q4_K_M (~300MB)")
    print("="*70)
    
    try:
        from llama_cpp import Llama
        import time
        
        start = time.time()
        print("\n📥 Descargando desde HuggingFace...")
        print("   Repo: Qwen/Qwen2.5-0.5B-Instruct-GGUF")
        print("   Archivo: qwen2.5-0.5b-instruct-q4_k_m.gguf")
        print("   (Esto puede tomar 1-5 minutos dependiendo de tu conexión)\n")
        
        llm = Llama.from_pretrained(
            repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
            filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
            n_ctx=2048,
            n_threads=4,
            verbose=True
        )
        
        elapsed = time.time() - start
        print(f"\n✅ LLM descargado exitosamente en {elapsed:.1f}s")
        print(f"   Guardado en cache de HuggingFace")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error descargando LLM: {e}")
        print("\n💡 Sugerencias:")
        print("   • Verifica tu conexión a internet")
        print("   • Intenta de nuevo (el progreso se guarda)")
        print("   • O descarga manualmente desde:")
        print("     https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF")
        return False

def download_asr():
    """Descarga el modelo ASR (Whisper tiny.en)"""
    print("\n" + "="*70)
    print("Descargando ASR: Whisper tiny.en (~75MB)")
    print("="*70)
    
    try:
        from faster_whisper import WhisperModel
        import time
        
        start = time.time()
        print("\n📥 Descargando desde HuggingFace...")
        print("   Modelo: tiny.en")
        print("   (Esto puede tomar 30s-2min dependiendo de tu conexión)\n")
        
        model = WhisperModel(
            "tiny.en",
            device="cpu",
            compute_type="int8",
            download_root=None  # Usa cache por defecto
        )
        
        elapsed = time.time() - start
        print(f"\n✅ ASR descargado exitosamente en {elapsed:.1f}s")
        print(f"   Guardado en cache de HuggingFace")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error descargando ASR: {e}")
        print("\n💡 Sugerencias:")
        print("   • Verifica tu conexión a internet")
        print("   • Intenta de nuevo")
        print("   • El modelo se descarga automáticamente al usar WhisperModel()")
        return False

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              DESCARGA DE MODELOS PARA TESTS REALES                  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    print("\n🎯 Este script descargará:")
    print("   1. LLM: Qwen 0.5B Q4_K_M (~300MB)")
    print("   2. ASR: Whisper tiny.en (~75MB)")
    print("   Total: ~375MB")
    print("\n⚠️  REQUIERE INTERNET ⚠️")
    print()
    
    input("Presiona ENTER para continuar (o Ctrl+C para cancelar)...")
    
    results = {}
    
    # Descargar LLM
    results['llm'] = download_llm()
    
    # Descargar ASR
    results['asr'] = download_asr()
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE DESCARGA")
    print("="*70)
    
    if results['llm']:
        print("\n✅ LLM (Qwen 0.5B): Descargado y en cache")
    else:
        print("\n❌ LLM (Qwen 0.5B): Error en descarga")
    
    if results['asr']:
        print("✅ ASR (Whisper tiny.en): Descargado y en cache")
    else:
        print("❌ ASR (Whisper tiny.en): Error en descarga")
    
    if all(results.values()):
        print("\n" + "="*70)
        print("🎉 TODOS LOS MODELOS DESCARGADOS EXITOSAMENTE")
        print("="*70)
        print("\nAhora puedes ejecutar:")
        print("   python3 test_real_performance.py")
        print("\nPara ver benchmarks reales de velocidad.")
        return 0
    else:
        print("\n" + "="*70)
        print("⚠️ ALGUNOS MODELOS NO SE DESCARGARON")
        print("="*70)
        print("\nRevisa los errores arriba e intenta de nuevo.")
        print("Los modelos parcialmente descargados se reanudarán.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
