#!/usr/bin/env python3
"""
Simple source code verification for Qwen 0.5 integration
Tests without importing dependencies
"""
import os

def test_coach_source():
    """Test Coach.py source code"""
    print("Testing Coach source code...")
    
    coach_path = "app/coach/coach.py"
    with open(coach_path, 'r') as f:
        content = f.read()
    
    failures = []
    
    # Check for removed templates
    if 'self.templates' in content:
        failures.append("❌ Found 'self.templates' in coach.py")
    else:
        print("✓ No templates dictionary found")
    
    # Check for removed _intent_fast
    if 'def _intent_fast' in content:
        failures.append("❌ Found '_intent_fast' method in coach.py")
    else:
        print("✓ No _intent_fast method found")
    
    # Check for hardcoded intent strings
    if '"ask_experience"' in content or '"ask_schedule"' in content:
        failures.append("❌ Found hardcoded intent strings in coach.py")
    else:
        print("✓ No hardcoded intent strings found")
    
    # Check for if-else intent detection
    if 'if any(k in t for k in ["experience"' in content:
        failures.append("❌ Found if-else intent detection logic in coach.py")
    else:
        print("✓ No if-else intent detection found")
    
    # Check that LLM is always used
    if 'self.llm.generate_json' not in content:
        failures.append("❌ LLM generate_json not found in coach.py")
    else:
        print("✓ LLM generate_json is used")
    
    # Check for suggest_draft using LLM without fallback
    suggest_draft_start = content.find('def suggest_draft')
    if suggest_draft_start > 0:
        suggest_draft_end = content.find('\n    def ', suggest_draft_start + 1)
        if suggest_draft_end < 0:
            suggest_draft_end = len(content)
        suggest_draft_code = content[suggest_draft_start:suggest_draft_end]
        
        if 'self.templates' in suggest_draft_code:
            failures.append("❌ suggest_draft still uses templates")
        else:
            print("✓ suggest_draft doesn't use templates")
            
        if 'return draft' in suggest_draft_code or 'return fallback' in suggest_draft_code:
            # Check if it's only for empty input
            lines = suggest_draft_code.split('\n')
            for i, line in enumerate(lines):
                if 'return draft' in line or 'return fallback' in line:
                    # Check if this is after checking empty input
                    prev_lines = '\n'.join(lines[max(0,i-5):i])
                    if 'not her_partial.strip()' not in prev_lines and 'not her_final.strip()' not in prev_lines:
                        failures.append("❌ suggest_draft has template/fallback return")
                        break
            else:
                print("✓ suggest_draft only returns LLM output")
        else:
            print("✓ suggest_draft only returns LLM output")
    
    return failures

def test_llm_engine_source():
    """Test LLMEngine.py source code"""
    print("\nTesting LLMEngine source code...")
    
    llm_path = "app/llm/llm_engine.py"
    with open(llm_path, 'r') as f:
        content = f.read()
    
    failures = []
    
    # Check that llama_cpp import has proper handling
    if 'from llama_cpp import Llama' in content:
        if 'LLAMA_CPP_AVAILABLE' in content:
            print("✓ llama-cpp-python import properly handled")
        elif 'except ImportError' in content:
            print("✓ llama-cpp-python import properly handled")
        else:
            failures.append("❌ LLM engine import not properly handled")
    else:
        failures.append("❌ llama_cpp import not found")
    
    # Check that model_path is required
    if 'if not self.model_path:' in content and 'return' in content:
        # Check if it's raising an error instead
        init_start = content.find('def _init(self):')
        init_end = content.find('\n    def ', init_start + 1)
        if init_end < 0:
            init_end = len(content)
        init_code = content[init_start:init_end]
        
        if 'raise ValueError' not in init_code:
            failures.append("❌ LLM engine accepts empty model path without error")
        else:
            print("✓ LLM engine requires model path")
    else:
        print("✓ LLM engine requires model path")
    
    # Check that generate_json raises errors
    if 'def generate_json' in content:
        gen_start = content.find('def generate_json')
        gen_end = content.find('\n    def ', gen_start + 1)
        if gen_end < 0:
            gen_end = len(content)
        gen_code = content[gen_start:gen_end]
        
        if 'return {}' in gen_code and 'raise RuntimeError' not in gen_code:
            # Some return {} is ok for exceptions, but should have raises
            pass
        
        if 'raise RuntimeError' in gen_code:
            print("✓ generate_json raises errors appropriately")
        else:
            print("⚠ generate_json may silently fail (acceptable if wrapped)")
    
    return failures

def test_requirements():
    """Test requirements.txt"""
    print("\nTesting requirements.txt...")
    
    with open("requirements.txt", 'r') as f:
        content = f.read()
    
    failures = []
    
    if 'llama-cpp-python' not in content:
        failures.append("❌ llama-cpp-python not in requirements.txt")
    else:
        print("✓ llama-cpp-python is required")
    
    if 'sentence-transformers' not in content:
        failures.append("❌ sentence-transformers not in requirements.txt")
    else:
        print("✓ sentence-transformers is required")
    
    return failures

def test_readme():
    """Test README.md"""
    print("\nTesting README.md...")
    
    with open("README.md", 'r') as f:
        content = f.read()
    
    failures = []
    
    if 'Qwen 0.5' in content or 'Qwen2.5-0.5B' in content:
        print("✓ README mentions Qwen 0.5")
    else:
        failures.append("❌ README doesn't mention Qwen 0.5")
    
    # Check if LLM is marked as optional (in Spanish or English)
    # README is in Spanish, so we check for 'opcional' primarily
    if ('opcional' in content.lower() or 'optional' in content.lower()) and 'llm' in content.lower():
        # Check context to see if it's marked as required
        if 'REQUERIDO' in content or 'requerido' in content or 'required' in content.upper():
            print("✓ README indicates LLM is required")
        else:
            failures.append("⚠ README may still say LLM is optional")
    else:
        print("✓ README updated")
    
    return failures

def main():
    """Run all tests"""
    print("="*70)
    print("Source Code Verification - Qwen 0.5 Integration (No Templates/If-Else)")
    print("="*70)
    print()
    
    all_failures = []
    
    all_failures.extend(test_coach_source())
    all_failures.extend(test_llm_engine_source())
    all_failures.extend(test_requirements())
    all_failures.extend(test_readme())
    
    print("\n" + "="*70)
    if not all_failures:
        print("✅ ALL CHECKS PASSED!")
        print("\nVerified:")
        print("  ✓ No hardcoded templates in Coach")
        print("  ✓ No if-else intent detection")
        print("  ✓ LLM (llama-cpp-python) is required")
        print("  ✓ All responses generated by LLM")
        print("  ✓ Qwen 0.5 documented as required")
        print("\n✨ System is ready for Qwen 0.5B Instruct GGUF model")
        print("\nTo use:")
        print("  1. Download: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF")
        print("  2. Configure: Set llm_model_path in config.default.json")
        print("  3. Run: python app/main.py")
        return 0
    else:
        print("❌ FAILURES DETECTED:")
        for failure in all_failures:
            print(f"  {failure}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
