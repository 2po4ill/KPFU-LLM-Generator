"""
Monitor GPU usage during generation
"""
import asyncio
import time
import sys
import subprocess
sys.path.insert(0, 'app')
from core.model_manager import ModelManager

async def test_with_monitoring():
    """Test with GPU monitoring"""
    print("🔧 Initializing ModelManager...")
    model_manager = ModelManager()
    await model_manager.initialize()
    
    llm = await model_manager.get_llm_model()
    
    prompt = "Напиши короткую лекцию о функциях в Python (200 слов)."
    
    print(f"\n📝 Starting generation...")
    print("=" * 80)
    
    # Check GPU before
    result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'], 
                          capture_output=True, text=True)
    print(f"GPU BEFORE: {result.stdout.strip()}")
    
    start_time = time.time()
    
    # Start generation
    response = await llm.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.3,
            "num_predict": 500,
            "top_p": 0.9
        }
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Check GPU after
    result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'], 
                          capture_output=True, text=True)
    print(f"GPU AFTER: {result.stdout.strip()}")
    
    content = response.get('response', '')
    estimated_tokens = len(content) / 4
    tokens_per_second = estimated_tokens / elapsed
    
    print(f"\n⏱️  Time: {elapsed:.2f}s")
    print(f"🚀 Speed: ~{tokens_per_second:.0f} tokens/second")
    print(f"📊 Tokens: ~{estimated_tokens:.0f}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_with_monitoring())
