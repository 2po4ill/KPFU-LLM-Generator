"""
Test GPU performance for Ollama
"""
import asyncio
import time
import sys
sys.path.insert(0, 'app')
from core.model_manager import ModelManager

async def test_generation_speed():
    """Test token generation speed"""
    print("🔧 Initializing ModelManager...")
    model_manager = ModelManager()
    await model_manager.initialize()
    
    llm = await model_manager.get_llm_model()
    
    prompt = "Напиши подробную лекцию о функциях в Python. Объясни определение функций, параметры, возврат значений, и приведи 5 примеров кода."
    
    print(f"\n📝 Generating with prompt ({len(prompt)} chars)...")
    print("=" * 80)
    
    start_time = time.time()
    
    response = await llm.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.3,
            "num_predict": 1000,  # Generate 1000 tokens
            "top_p": 0.9
        }
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    content = response.get('response', '')
    
    # Estimate tokens (rough: 1 token ≈ 4 chars for Russian)
    estimated_tokens = len(content) / 4
    tokens_per_second = estimated_tokens / elapsed
    
    print(f"\n⏱️  Generation Time: {elapsed:.2f}s")
    print(f"📊 Generated: ~{estimated_tokens:.0f} tokens")
    print(f"🚀 Speed: ~{tokens_per_second:.0f} tokens/second")
    print(f"💾 Content length: {len(content)} chars")
    
    if tokens_per_second < 300:
        print("\n⚠️  WARNING: Speed is slow - likely using CPU!")
        print("   Expected GPU speed: 600-1000 tokens/s")
    elif tokens_per_second < 600:
        print("\n✓ Using GPU, but performance could be better")
        print("  Try closing other GPU-heavy apps")
    else:
        print("\n✓ Excellent GPU performance!")
    
    print("\n" + "=" * 80)
    print("Sample output:")
    print(content[:500] + "...")

if __name__ == "__main__":
    asyncio.run(test_generation_speed())
