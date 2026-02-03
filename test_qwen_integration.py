#!/usr/bin/env python3
"""
Test script to verify Qwen 0.5 integration without templates/if-else
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from app.coach.coach import Coach
        print("✓ Coach module imported")
        
        from app.llm.llm_engine import LLMEngine
        print("✓ LLMEngine module imported")
        
        from app.coach.embedder import Embedder
        print("✓ Embedder module imported")
        
        from app.coach.translator import TranslatorENES
        print("✓ Translator module imported")
        
        from app.rag.pdf_store import DocumentStore
        print("✓ DocumentStore module imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_no_templates():
    """Verify that Coach class doesn't have template attributes"""
    print("\nTesting for absence of templates...")
    try:
        from app.coach.coach import Coach
        
        # Check if Coach has templates attribute
        coach_attrs = dir(Coach)
        if 'templates' in coach_attrs:
            print("✗ Coach class still has 'templates' attribute")
            return False
        
        # Check the source code doesn't contain template definitions
        import inspect
        source = inspect.getsource(Coach)
        
        if 'self.templates' in source:
            print("✗ Coach source code contains 'self.templates'")
            return False
            
        print("✓ No templates found in Coach class")
        return True
    except Exception as e:
        print(f"✗ Template check failed: {e}")
        return False

def test_no_intent_fast():
    """Verify that _intent_fast method with if-else is removed"""
    print("\nTesting for absence of _intent_fast method...")
    try:
        from app.coach.coach import Coach
        import inspect
        
        source = inspect.getsource(Coach)
        
        if '_intent_fast' in source:
            print("✗ Coach source code still contains '_intent_fast'")
            return False
            
        if 'ask_experience' in source or 'ask_schedule' in source:
            print("✗ Coach source code still contains hardcoded intent strings")
            return False
            
        print("✓ No _intent_fast method found in Coach class")
        return True
    except Exception as e:
        print(f"✗ Intent check failed: {e}")
        return False

def test_llm_required():
    """Test that LLM module requires proper initialization"""
    print("\nTesting LLM requirement...")
    try:
        from app.llm.llm_engine import LLMEngine
        
        # Try to create engine with empty model path (should fail)
        try:
            engine = LLMEngine("", 2048, 4)
            print("✗ LLMEngine accepted empty model path")
            return False
        except (ValueError, FileNotFoundError) as e:
            print(f"✓ LLMEngine correctly rejects empty/invalid model path: {type(e).__name__}")
            
        return True
    except Exception as e:
        print(f"✗ LLM requirement check failed: {e}")
        return False

def test_coach_depends_on_llm():
    """Test that Coach methods always use LLM"""
    print("\nTesting Coach LLM dependency...")
    try:
        from app.coach.coach import Coach
        import inspect
        
        # Get source code of suggest_draft and suggest_final
        source = inspect.getsource(Coach.suggest_draft)
        source += inspect.getsource(Coach.suggest_final)
        
        # Check that there are no fallback templates
        if 'self.templates' in source:
            print("✗ Coach methods still reference templates")
            return False
            
        # Check that LLM generate_json is called
        if 'self.llm.generate_json' not in source:
            print("✗ Coach methods don't call LLM")
            return False
            
        print("✓ Coach methods depend on LLM, no template fallbacks")
        return True
    except Exception as e:
        print(f"✗ Coach LLM dependency check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("Qwen 0.5 Integration Verification Tests")
    print("="*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("No Templates", test_no_templates()))
    results.append(("No If-Else Intent", test_no_intent_fast()))
    results.append(("LLM Required", test_llm_required()))
    results.append(("Coach LLM Dependency", test_coach_depends_on_llm()))
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<30} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("="*60)
    if all_passed:
        print("✓ All tests PASSED")
        print("\nThe system is configured to:")
        print("  - Require Qwen 0.5 LLM (no templates or if-else)")
        print("  - Use llama-cpp-python for GGUF models")
        print("  - Generate all responses from LLM")
        print("\nNext steps:")
        print("  1. Download Qwen 2.5 0.5B Instruct GGUF model")
        print("  2. Configure llm_model_path in config")
        print("  3. Run the application")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
