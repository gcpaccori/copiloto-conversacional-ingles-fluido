#!/usr/bin/env python3
"""
Test script to verify ASR model loading with HuggingFace access
"""
import sys
import os

def test_asr_loading():
    print("="*70)
    print("Testing ASR Model Loading")
    print("="*70)
    
    try:
        from faster_whisper import WhisperModel
        print("✅ faster-whisper imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import faster-whisper: {e}")
        print("Installing faster-whisper...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "faster-whisper"])
        from faster_whisper import WhisperModel
        print("✅ faster-whisper installed and imported")
    
    print("\n" + "="*70)
    print("Test 1: Loading from HuggingFace repo")
    print("="*70)
    
    try:
        print("\n📥 Attempting to load: Systran/faster-whisper-tiny.en")
        model = WhisperModel(
            "Systran/faster-whisper-tiny.en",
            device="cpu",
            compute_type="int8"
        )
        print("✅ Successfully loaded model from HuggingFace!")
        print(f"   Model is ready: {model is not None}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to load model: {e}")
        
        # Check for blocked domains
        if "No address associated with hostname" in error_msg or "ConnectError" in error_msg:
            print("\n🚫 DOMAIN BLOCKED:")
            print("   The download failed due to network restrictions.")
            print("   Required domains: huggingface.co, cdn-lfs.huggingface.co")
        
        return False

if __name__ == "__main__":
    success = test_asr_loading()
    sys.exit(0 if success else 1)
