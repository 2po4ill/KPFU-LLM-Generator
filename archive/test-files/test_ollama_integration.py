"""
Test Ollama integration
Run after installing Ollama and downloading llama3.1:8b

Run with: python test_ollama_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))


async def test_ollama_connection():
    """Test basic Ollama connection"""
    print("=" * 70)
    print("Testing Ollama Integration")
    print("=" * 70)
    
    try:
        import ollama
        
        print("\n✓ Ollama Python client installed")
        
        # Test connection
        print("\n📡 Testing connection to Ollama server...")
        try:
            models = ollama.list()
            print(f"✓ Connected to Ollama server")
            
            model_list = models.get('models', [])
            print(f"  Available models: {len(model_list)}")
            
            for model in model_list:
                model_name = model.get('model', model.get('name', 'unknown'))
                print(f"    - {model_name}")
            
        except Exception as e:
            print(f"❌ Cannot connect to Ollama server: {e}")
            print(f"\nMake sure Ollama is running:")
            print(f"  1. Check if Ollama service is started")
            print(f"  2. Try: ollama serve")
            return False
        
        # Test generation
        print("\n🤖 Testing text generation...")
        try:
            response = ollama.generate(
                model='llama3.1:8b',
                prompt='Напиши короткое приветствие на русском языке.',
                options={
                    'temperature': 0.7,
                    'num_predict': 50
                }
            )
            
            print(f"✓ Generation successful!")
            print(f"\nResponse:")
            print(f"  {response['response'][:200]}...")
            
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            
            if "model 'llama3.1:8b' not found" in str(e):
                print(f"\nModel not found. Download it with:")
                print(f"  ollama pull llama3.1:8b")
            
            return False
        
        print("\n" + "=" * 70)
        print("✅ Ollama integration test PASSED!")
        print("=" * 70)
        return True
        
    except ImportError:
        print("❌ Ollama Python client not installed")
        print("\nInstall with: pip install ollama")
        return False


async def test_with_model_manager():
    """Test Ollama with ModelManager"""
    print("\n" + "=" * 70)
    print("Testing with ModelManager")
    print("=" * 70)
    
    try:
        from core.model_manager import ModelManager
        
        print("\n🔧 Initializing ModelManager...")
        model_manager = ModelManager(use_mock_services=False)
        await model_manager.initialize()
        
        print("✓ ModelManager initialized")
        
        # Test LLM generation
        print("\n🤖 Testing LLM generation through ModelManager...")
        llm_model = await model_manager.get_llm_model()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt="Объясни что такое Python в одном предложении.",
            options={
                "temperature": 0.3,
                "num_predict": 100
            }
        )
        
        print(f"✓ Generation successful!")
        print(f"\nResponse:")
        print(f"  {response.get('response', '')[:300]}...")
        
        # Cleanup
        await model_manager.cleanup()
        
        print("\n" + "=" * 70)
        print("✅ ModelManager integration test PASSED!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ ModelManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_russian_content_generation():
    """Test Russian content generation"""
    print("\n" + "=" * 70)
    print("Testing Russian Content Generation")
    print("=" * 70)
    
    try:
        import ollama
        
        prompt = """Создай короткую лекцию о переменных в Python.

Структура:
1. Что такое переменные
2. Как создать переменную
3. Пример

Пиши на русском языке, академическим стилем."""
        
        print("\n📝 Generating lecture content...")
        print(f"Prompt: {prompt[:100]}...")
        
        response = ollama.generate(
            model='llama3.1:8b',
            prompt=prompt,
            options={
                'temperature': 0.3,
                'num_predict': 500
            }
        )
        
        content = response['response']
        
        print(f"\n✓ Generated {len(content)} characters")
        print(f"\n📄 Generated Content:")
        print("-" * 70)
        print(content[:500])
        if len(content) > 500:
            print(f"... ({len(content) - 500} more characters)")
        print("-" * 70)
        
        print("\n" + "=" * 70)
        print("✅ Russian content generation test PASSED!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Russian content test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n🚀 Starting Ollama Integration Tests\n")
    
    # Test 1: Basic connection
    test1 = await test_ollama_connection()
    
    if not test1:
        print("\n⚠️  Basic connection test failed. Fix issues before continuing.")
        return
    
    # Test 2: ModelManager integration
    test2 = await test_with_model_manager()
    
    # Test 3: Russian content
    test3 = await test_russian_content_generation()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"  Basic Connection: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  ModelManager: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"  Russian Content: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 All tests PASSED! Ollama is ready for production use.")
        print("\nNext step: Run the complete pipeline with real LLM:")
        print("  python test_complete_pipeline.py --use-real-llm")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
