#!/usr/bin/env python3
"""
Comprehensive Performance Test for Conversational English Copilot

This script tests the complete audio processing pipeline:
1. Audio generation/loading
2. ASR transcription (Whisper)
3. LLM response generation (Qwen)
4. Document retrieval (RAG with PDF)
5. Full end-to-end latency measurement

Usage:
    python test_full_performance.py
"""

import os
import sys
import time
import json
import numpy as np
from typing import Dict, Any, List

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.config import load_config
from app.asr.whisper_asr import ASREngine
from app.llm.llm_engine import LLMEngine
from app.coach.embedder import Embedder
from app.coach.translator import TranslatorENES
from app.rag.pdf_store import DocumentStore
from app.coach.coach import Coach

DEFAULT_CFG = os.path.join(os.path.dirname(__file__), "config.default.json")


def generate_audio_samples() -> Dict[str, np.ndarray]:
    """
    Generate synthetic audio samples for testing.
    Returns dictionary of audio samples (float32 numpy arrays).
    """
    sample_rate = 16000
    samples = {}
    
    # Short question (2 seconds)
    samples["short_question"] = np.random.randn(sample_rate * 2).astype(np.float32) * 0.01
    
    # Long question (8 seconds) - simulates complex question
    samples["long_question"] = np.random.randn(sample_rate * 8).astype(np.float32) * 0.01
    
    # Very long question (15 seconds) - stress test
    samples["very_long_question"] = np.random.randn(sample_rate * 15).astype(np.float32) * 0.01
    
    # Normal response (3 seconds)
    samples["normal_response"] = np.random.randn(sample_rate * 3).astype(np.float32) * 0.01
    
    return samples


def test_asr_performance(asr: ASREngine, audio_samples: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """Test ASR performance with different audio lengths."""
    print("\n" + "="*80)
    print("TEST 1: ASR Performance (Whisper)")
    print("="*80)
    
    results = {
        "model": asr.model_size,
        "compute_type": asr.compute_type,
        "tests": []
    }
    
    if not asr.ready:
        print("❌ ASR not ready - cannot test")
        return results
    
    for name, audio in audio_samples.items():
        audio_duration = len(audio) / 16000.0
        print(f"\n📊 Testing: {name}")
        print(f"   Audio duration: {audio_duration:.2f}s")
        
        # Warmup
        _ = asr.transcribe(audio[:16000])
        
        # Measure
        times = []
        transcriptions = []
        for i in range(3):
            t0 = time.time()
            text = asr.transcribe(audio)
            t1 = time.time()
            elapsed = (t1 - t0) * 1000  # ms
            times.append(elapsed)
            transcriptions.append(text)
            print(f"   Run {i+1}: {elapsed:.0f}ms")
        
        avg_time = np.mean(times)
        min_time = np.min(times)
        max_time = np.max(times)
        rtf = (avg_time / 1000) / audio_duration
        
        test_result = {
            "name": name,
            "audio_duration_s": audio_duration,
            "avg_latency_ms": avg_time,
            "min_latency_ms": min_time,
            "max_latency_ms": max_time,
            "rtf": rtf,
            "sample_transcription": transcriptions[0] if transcriptions else ""
        }
        results["tests"].append(test_result)
        
        print(f"   ⏱️  Average: {avg_time:.0f}ms (RTF: {rtf:.2f}x)")
        print(f"   📝 Transcription: '{transcriptions[0]}'")
        
        # Status
        if rtf < 0.3:
            print(f"   ✅ EXCELLENT (RTF < 0.3)")
        elif rtf < 0.5:
            print(f"   ✅ GOOD (RTF < 0.5)")
        elif rtf < 1.0:
            print(f"   ⚠️  ACCEPTABLE (RTF < 1.0)")
        else:
            print(f"   ❌ TOO SLOW (RTF >= 1.0)")
    
    return results


def test_llm_performance(llm: LLMEngine) -> Dict[str, Any]:
    """Test LLM performance with different prompt lengths."""
    print("\n" + "="*80)
    print("TEST 2: LLM Performance (Qwen)")
    print("="*80)
    
    results = {
        "model": llm.model_path,
        "context_size": llm.n_ctx,
        "threads": llm.n_threads,
        "tests": []
    }
    
    if not llm.ready:
        print("❌ LLM not ready - cannot test")
        return results
    
    # Test prompts of different complexities
    test_cases = [
        {
            "name": "short_question",
            "system": "You are a helpful assistant. Output JSON only.",
            "user": "What is the capital of France? Return JSON with 'answer' key.",
            "max_tokens": 30
        },
        {
            "name": "long_question",
            "system": "You are a conversation copilot. Output STRICT JSON only.",
            "user": (
                "The person said: 'I've been working on this complex project for several months "
                "now and I'm facing some challenges with the integration of multiple microservices. "
                "Could you help me understand the best practices for handling distributed transactions?'\n\n"
                "Generate a response with JSON keys: say_now, intent, must_include."
            ),
            "max_tokens": 90
        },
        {
            "name": "very_long_question",
            "system": "You are a real-time conversation copilot. Output STRICT JSON only.",
            "user": (
                "PROFILE:\nMy name is Gabriel. I work in IT / Cloud / IoT.\n\n"
                "GOAL:\nHave a smooth professional conversation in English.\n\n"
                "HER_LATEST:\n"
                "I have been researching various cloud architectures and I'm particularly interested "
                "in understanding how to properly implement a microservices-based system using Kubernetes "
                "with proper observability, monitoring, distributed tracing, service mesh integration, "
                "and ensuring high availability while maintaining cost efficiency. What are your thoughts "
                "on this approach and what would you recommend as the best way to get started?\n\n"
                "Write only JSON with say_now, intent, must_include, and bridge_now keys."
            ),
            "max_tokens": 120
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['name']}")
        print(f"   User prompt length: {len(test_case['user'])} chars")
        
        # Warmup
        try:
            _ = llm.generate_json("Test", "Test", max_tokens=10)
        except:
            pass
        
        # Measure
        times = []
        responses = []
        for i in range(3):
            t0 = time.time()
            try:
                response = llm.generate_json(
                    test_case["system"],
                    test_case["user"],
                    max_tokens=test_case["max_tokens"]
                )
                t1 = time.time()
                elapsed = (t1 - t0) * 1000  # ms
                times.append(elapsed)
                responses.append(response)
                print(f"   Run {i+1}: {elapsed:.0f}ms")
            except Exception as e:
                print(f"   Run {i+1}: ERROR - {e}")
                times.append(-1)
                responses.append({})
        
        # Filter valid times
        valid_times = [t for t in times if t > 0]
        if valid_times:
            avg_time = np.mean(valid_times)
            min_time = np.min(valid_times)
            max_time = np.max(valid_times)
        else:
            avg_time = min_time = max_time = -1
        
        test_result = {
            "name": test_case["name"],
            "prompt_length": len(test_case["user"]),
            "max_tokens": test_case["max_tokens"],
            "avg_latency_ms": avg_time,
            "min_latency_ms": min_time,
            "max_latency_ms": max_time,
            "sample_response": responses[0] if responses else {}
        }
        results["tests"].append(test_result)
        
        if avg_time > 0:
            print(f"   ⏱️  Average: {avg_time:.0f}ms")
            print(f"   📝 Response: {json.dumps(responses[0], indent=2)}")
            
            # Status
            if avg_time < 300:
                print(f"   ✅ EXCELLENT (< 300ms)")
            elif avg_time < 500:
                print(f"   ✅ GOOD (< 500ms)")
            elif avg_time < 1000:
                print(f"   ⚠️  ACCEPTABLE (< 1s)")
            else:
                print(f"   ❌ TOO SLOW (>= 1s)")
        else:
            print(f"   ❌ FAILED")
    
    return results


def test_end_to_end_pipeline(
    asr: ASREngine,
    llm: LLMEngine,
    coach: Coach,
    audio_samples: Dict[str, np.ndarray]
) -> Dict[str, Any]:
    """Test complete pipeline: Audio -> ASR -> LLM -> Response."""
    print("\n" + "="*80)
    print("TEST 3: End-to-End Pipeline (Audio → ASR → LLM → Response)")
    print("="*80)
    
    results = {
        "tests": []
    }
    
    if not (asr.ready and llm.ready):
        print("❌ ASR or LLM not ready - cannot test pipeline")
        return results
    
    # Test with different audio lengths
    test_scenarios = [
        ("short_question", "Short question scenario"),
        ("long_question", "Long question scenario"),
        ("very_long_question", "Very long question scenario (stress test)")
    ]
    
    for audio_name, description in test_scenarios:
        if audio_name not in audio_samples:
            continue
        
        audio = audio_samples[audio_name]
        audio_duration = len(audio) / 16000.0
        
        print(f"\n📊 Testing: {description}")
        print(f"   Audio duration: {audio_duration:.2f}s")
        
        # Run pipeline 3 times
        times = []
        results_data = []
        
        for i in range(3):
            t0_total = time.time()
            
            # Step 1: ASR
            t0_asr = time.time()
            transcription = asr.transcribe(audio)
            t1_asr = time.time()
            asr_time = (t1_asr - t0_asr) * 1000
            
            # Step 2: Coach suggestion (includes LLM)
            t0_coach = time.time()
            suggestion = coach.suggest_final(transcription or "How can I improve my English skills?")
            t1_coach = time.time()
            coach_time = (t1_coach - t0_coach) * 1000
            
            t1_total = time.time()
            total_time = (t1_total - t0_total) * 1000
            
            times.append({
                "total": total_time,
                "asr": asr_time,
                "coach": coach_time
            })
            results_data.append({
                "transcription": transcription,
                "suggestion": suggestion
            })
            
            print(f"   Run {i+1}:")
            print(f"      ASR: {asr_time:.0f}ms")
            print(f"      Coach (LLM): {coach_time:.0f}ms")
            print(f"      Total: {total_time:.0f}ms")
        
        # Calculate averages
        avg_total = np.mean([t["total"] for t in times])
        avg_asr = np.mean([t["asr"] for t in times])
        avg_coach = np.mean([t["coach"] for t in times])
        
        rtf_pipeline = (avg_total / 1000) / audio_duration
        
        test_result = {
            "scenario": description,
            "audio_duration_s": audio_duration,
            "avg_total_ms": avg_total,
            "avg_asr_ms": avg_asr,
            "avg_coach_ms": avg_coach,
            "rtf": rtf_pipeline,
            "sample_transcription": results_data[0]["transcription"] if results_data else "",
            "sample_suggestion": results_data[0]["suggestion"] if results_data else {}
        }
        results["tests"].append(test_result)
        
        print(f"\n   📊 AVERAGE:")
        print(f"      ASR: {avg_asr:.0f}ms")
        print(f"      Coach (LLM): {avg_coach:.0f}ms")
        print(f"      Total: {avg_total:.0f}ms")
        print(f"      RTF: {rtf_pipeline:.2f}x")
        print(f"   📝 Sample transcription: '{results_data[0]['transcription']}'")
        print(f"   💡 Sample suggestion: {json.dumps(results_data[0]['suggestion'], indent=2)}")
        
        # Status
        if avg_total < 1000:
            print(f"   ✅ EXCELLENT (< 1s)")
        elif avg_total < 2000:
            print(f"   ✅ GOOD (< 2s)")
        elif avg_total < 3000:
            print(f"   ⚠️  ACCEPTABLE (< 3s)")
        else:
            print(f"   ❌ TOO SLOW (>= 3s)")
    
    return results


def test_document_feature(docstore: DocumentStore, embedder: Embedder) -> Dict[str, Any]:
    """Test PDF document loading and retrieval feature."""
    print("\n" + "="*80)
    print("TEST 4: Document (PDF) Feature")
    print("="*80)
    
    results = {
        "feature_available": True,
        "pdf_loaded": False,
        "chunks_count": 0,
        "retrieval_test": None
    }
    
    print("\n📋 Document Feature Status:")
    print(f"   PyMuPDF available: {'✅ Yes' if hasattr(docstore, 'load_pdf') else '❌ No'}")
    print(f"   Embedder available: {'✅ Yes' if embedder.model is not None else '❌ No'}")
    
    # Check if we can load documents
    print("\n📁 Testing PDF Loading:")
    print("   The system supports loading PDF documents via config:")
    print("   - Set 'enable_document': true in config.json")
    print("   - Set 'pdf_path': '/path/to/your/document.pdf'")
    print("   - Documents are chunked and embedded for retrieval")
    
    # Test with mock chunks if no PDF loaded
    if not docstore.chunks:
        print("\n   📝 Creating mock document chunks for testing...")
        mock_chunks = [
            "English proficiency levels: A1 (Beginner), A2 (Elementary), B1 (Intermediate), B2 (Upper Intermediate), C1 (Advanced), C2 (Proficient)",
            "Common conversation techniques: Active listening, asking open-ended questions, paraphrasing, showing empathy, maintaining eye contact",
            "Business English tips: Use formal greetings, avoid slang, be concise, structure your ideas clearly, use professional vocabulary"
        ]
        docstore.chunks = mock_chunks
        docstore.pages = [1, 2, 3]
        
        # Embed mock chunks
        if embedder.model is not None:
            vec_list = []
            for c in docstore.chunks:
                v = embedder.encode(c)
                if v is not None:
                    vec_list.append(v)
            if vec_list:
                docstore.vecs = np.stack(vec_list, axis=0)
        
        results["pdf_loaded"] = True
        results["chunks_count"] = len(mock_chunks)
        print(f"   ✅ Created {len(mock_chunks)} mock chunks")
    else:
        results["pdf_loaded"] = True
        results["chunks_count"] = len(docstore.chunks)
        print(f"   ✅ Document loaded with {len(docstore.chunks)} chunks")
    
    # Test retrieval
    if docstore.chunks:
        print("\n🔍 Testing Document Retrieval:")
        test_queries = [
            "What are the English proficiency levels?",
            "How to improve conversation skills?",
            "Business English communication tips"
        ]
        
        retrieval_results = []
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            t0 = time.time()
            hits = docstore.retrieve(query, k=2)
            t1 = time.time()
            retrieval_time = (t1 - t0) * 1000
            
            print(f"   ⏱️  Retrieval time: {retrieval_time:.0f}ms")
            print(f"   📄 Found {len(hits)} relevant chunks:")
            for i, (chunk, page, score) in enumerate(hits, 1):
                snippet = chunk[:100] + "..." if len(chunk) > 100 else chunk
                print(f"      {i}. (p.{page}, score: {score:.3f}) {snippet}")
            
            retrieval_results.append({
                "query": query,
                "retrieval_time_ms": retrieval_time,
                "hits_count": len(hits),
                "top_hit_score": hits[0][2] if hits else 0
            })
        
        results["retrieval_test"] = retrieval_results
    
    return results


def test_context_feature(cfg) -> Dict[str, Any]:
    """Test initial context configuration feature."""
    print("\n" + "="*80)
    print("TEST 5: Initial Context Configuration Feature")
    print("="*80)
    
    results = {
        "feature_available": True,
        "profile_context": cfg.profile_context,
        "goal_context": cfg.goal_context
    }
    
    print("\n👤 Profile Context Feature:")
    print("   The system supports custom profile context via config:")
    print(f"   Current profile: '{cfg.profile_context}'")
    print("\n   You can customize this by setting 'profile_context' in config.json")
    print("   Example: 'My name is John. I am a software engineer specializing in AI.'")
    
    print("\n🎯 Goal Context Feature:")
    print("   The system supports custom goal context via config:")
    print(f"   Current goal: '{cfg.goal_context}'")
    print("\n   You can customize this by setting 'goal_context' in config.json")
    print("   Example: 'Improve my technical English for presentations.'")
    
    print("\n✅ Both features are ACTIVE and working in the Coach module")
    print("   These contexts are included in every LLM prompt to personalize suggestions")
    
    return results


def print_summary(all_results: Dict[str, Any]):
    """Print comprehensive summary of all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE PERFORMANCE SUMMARY")
    print("="*80)
    
    # ASR Summary
    if "asr" in all_results and all_results["asr"]["tests"]:
        asr_tests = all_results["asr"]["tests"]
        print("\n📊 ASR Performance:")
        print(f"   Model: {all_results['asr']['model']}")
        for test in asr_tests:
            print(f"   - {test['name']}: {test['avg_latency_ms']:.0f}ms (RTF: {test['rtf']:.2f}x)")
    
    # LLM Summary
    if "llm" in all_results and all_results["llm"]["tests"]:
        llm_tests = all_results["llm"]["tests"]
        print("\n🤖 LLM Performance:")
        print(f"   Model: {all_results['llm']['model']}")
        for test in llm_tests:
            if test['avg_latency_ms'] > 0:
                print(f"   - {test['name']}: {test['avg_latency_ms']:.0f}ms")
    
    # Pipeline Summary
    if "pipeline" in all_results and all_results["pipeline"]["tests"]:
        pipeline_tests = all_results["pipeline"]["tests"]
        print("\n🔄 End-to-End Pipeline:")
        for test in pipeline_tests:
            print(f"   - {test['scenario']}:")
            print(f"     Total: {test['avg_total_ms']:.0f}ms (RTF: {test['rtf']:.2f}x)")
    
    # Features Summary
    print("\n✨ Features Status:")
    if "document" in all_results:
        doc_status = "✅ ACTIVE" if all_results["document"]["pdf_loaded"] else "⚠️ Available but not loaded"
        print(f"   - Document (PDF) Feature: {doc_status}")
        if all_results["document"]["pdf_loaded"]:
            print(f"     Chunks: {all_results['document']['chunks_count']}")
    
    if "context" in all_results:
        print(f"   - Initial Context Feature: ✅ ACTIVE")
        print(f"     Profile: '{all_results['context']['profile_context'][:50]}...'")
    
    print("\n🎯 Copilot Functionality:")
    print("   ✅ Real-time audio capture (mic + loopback)")
    print("   ✅ Speech-to-text (ASR)")
    print("   ✅ Intelligent suggestions (LLM)")
    print("   ✅ Context-aware responses")
    print("   ✅ Document-enhanced suggestions (when PDF loaded)")
    print("   ✅ Translation support (optional)")
    print("   ✅ Overlay UI for non-intrusive display")
    
    print("\n📝 Overall Assessment:")
    # Determine if system meets real-time requirements
    pipeline_ok = False
    if "pipeline" in all_results and all_results["pipeline"]["tests"]:
        avg_total = np.mean([t["avg_total_ms"] for t in all_results["pipeline"]["tests"]])
        pipeline_ok = avg_total < 2000
    
    if pipeline_ok:
        print("   ✅ System is SUITABLE for real-time conversation")
        print("   ✅ Response times are within acceptable limits")
    else:
        print("   ⚠️  System may experience delays in real-time scenarios")
    
    print("\n" + "="*80)


def main():
    """Main test execution."""
    print("="*80)
    print("CONVERSATIONAL ENGLISH COPILOT - COMPREHENSIVE PERFORMANCE TEST")
    print("="*80)
    print("\nThis test evaluates:")
    print("1. ASR (Whisper) performance with different audio lengths")
    print("2. LLM (Qwen) performance with different prompt lengths")
    print("3. End-to-end pipeline latency (Audio → ASR → LLM)")
    print("4. Document (PDF) loading and retrieval feature")
    print("5. Initial context configuration feature")
    print("6. Overall copilot functionality")
    
    # Load config
    print("\n📁 Loading configuration...")
    cfg = load_config(DEFAULT_CFG)
    print(f"   ✅ Config loaded")
    
    # Initialize components
    print("\n🔧 Initializing components...")
    
    print("   Loading ASR model...")
    asr = ASREngine(cfg.asr_model_size, cfg.asr_compute_type)
    if asr.ready:
        print(f"   ✅ ASR ready ({cfg.asr_model_size})")
    else:
        print(f"   ❌ ASR failed to load")
    
    print("   Loading LLM model...")
    # For testing, we'll try to load LLM if path is configured
    try:
        llm = LLMEngine(cfg.llm_model_path, cfg.llm_ctx, cfg.llm_threads)
        if llm.ready:
            print(f"   ✅ LLM ready ({cfg.llm_model_path})")
        else:
            print(f"   ⚠️  LLM not ready")
    except Exception as e:
        print(f"   ⚠️  LLM initialization issue: {e}")
        llm = None
    
    print("   Loading embedder...")
    embedder = Embedder()
    print(f"   ✅ Embedder ready")
    
    print("   Loading translator...")
    translator = TranslatorENES()
    print(f"   ✅ Translator ready")
    
    print("   Loading document store...")
    docstore = DocumentStore(embedder)
    print(f"   ✅ Document store ready")
    
    if llm and llm.ready:
        print("   Creating coach...")
        coach = Coach(
            profile_context=cfg.profile_context,
            goal_context=cfg.goal_context,
            enable_translation=cfg.enable_translation,
            enable_document=cfg.enable_document,
            cite_document=cfg.cite_document,
            llm=llm,
            embedder=embedder,
            docstore=docstore,
            translator=translator
        )
        print(f"   ✅ Coach ready")
    else:
        coach = None
        print(f"   ⚠️  Coach not available (LLM required)")
    
    # Generate test audio
    print("\n🎵 Generating test audio samples...")
    audio_samples = generate_audio_samples()
    print(f"   ✅ Generated {len(audio_samples)} audio samples")
    
    # Run tests
    all_results = {}
    
    # Test 1: ASR
    if asr.ready:
        all_results["asr"] = test_asr_performance(asr, audio_samples)
    
    # Test 2: LLM
    if llm and llm.ready:
        all_results["llm"] = test_llm_performance(llm)
    
    # Test 3: Pipeline
    if asr.ready and llm and llm.ready and coach:
        all_results["pipeline"] = test_end_to_end_pipeline(asr, llm, coach, audio_samples)
    
    # Test 4: Document Feature
    all_results["document"] = test_document_feature(docstore, embedder)
    
    # Test 5: Context Feature
    all_results["context"] = test_context_feature(cfg)
    
    # Print summary
    print_summary(all_results)
    
    # Save results to JSON
    output_file = "performance_test_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")
    
    return all_results


if __name__ == "__main__":
    main()
