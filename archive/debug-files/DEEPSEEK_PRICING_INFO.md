# DeepSeek Pricing Information

## Important: Ollama vs Direct API

**When using DeepSeek through Ollama with the `:cloud` suffix:**
- Ollama acts as a proxy to DeepSeek's API
- **You ARE charged** by DeepSeek (not by Ollama)
- Ollama itself is free, but it routes to DeepSeek's paid API

## DeepSeek API Pricing (2025)

**Model:** `deepseek-v3.2` (what `deepseek-v3.1:671b-cloud` uses)

### Costs per 1M tokens:
- **Input tokens (cache miss):** $0.28 per 1M tokens
- **Input tokens (cache hit):** $0.028 per 1M tokens (90% discount!)
- **Output tokens:** $0.42 per 1M tokens

### What is a token?
- A token is roughly 4 characters or 0.75 words
- Example: "Hello world" ≈ 2-3 tokens

## Cost Calculation for Our Use Case

### Per Lecture Generation:

**TOC Selection (4 chunks):**
- Input: ~6,000 tokens (4 chunks × 1,500 tokens each)
- Output: ~50 tokens (page ranges)
- Cost: (6,000 × $0.28 / 1M) + (50 × $0.42 / 1M) = **$0.0017** (~0.2 cents)

**Content Generation (using local Llama):**
- FREE - runs on your GPU

**Total per lecture:** ~$0.002 (0.2 cents)

### Monthly Estimates:

| Lectures/Month | Cost/Month |
|----------------|------------|
| 10 | $0.02 |
| 50 | $0.10 |
| 100 | $0.20 |
| 500 | $1.00 |
| 1000 | $2.00 |

## Cache Optimization

DeepSeek offers **90% discount on cached inputs**:
- If you query the same TOC multiple times, subsequent queries cost 10× less
- First query: $0.28 per 1M tokens
- Cached queries: $0.028 per 1M tokens

This is perfect for our use case - same book, different themes!

## Free Tier

According to [datastudios.org](https://www.datastudios.org/post/deepseek-v3-free-versions-access-tiers-usage-limits-and-availability-in-late-2025):
- DeepSeek offers a **free tier** for web app usage
- Free tier has usage limits (not specified)
- API access requires payment

**Important:** When using through Ollama cloud, you're using the API (not free tier).

## How to Set Up Billing

1. Create account at [https://platform.deepseek.com](https://platform.deepseek.com)
2. Add API key to Ollama (if required)
3. Top up balance (minimum varies)

## Alternative: Use Local Model

If you want to avoid costs entirely:

### Option 1: Use smaller local DeepSeek
```bash
ollama pull deepseek-v3:14b  # Smaller, runs locally
```
- Pros: Free, no API costs
- Cons: Lower quality than 671B cloud model

### Option 2: Use Llama 3.1 with chunking
- Already implemented as fallback
- Free, runs on your GPU
- Quality may be lower but acceptable

### Option 3: Hybrid approach
- Use DeepSeek cloud for TOC selection (cheap: $0.002/lecture)
- Use local Llama for content generation (free)
- **This is what we currently have!**

## Recommendation

**Keep the current hybrid approach:**
1. DeepSeek cloud for TOC selection - **$0.002 per lecture**
2. Local Llama 3.1 8B for content generation - **FREE**

**Why?**
- TOC selection is critical and needs high quality → DeepSeek
- Content generation is bulk work → Local GPU
- Total cost is negligible: $2 for 1000 lectures
- Best of both worlds: quality + cost efficiency

## Monitoring Costs

To track your DeepSeek usage:
1. Check dashboard at [https://platform.deepseek.com](https://platform.deepseek.com)
2. Monitor token usage in logs
3. Set up billing alerts

## Summary

✅ **Yes, DeepSeek cloud model is chargeable**
✅ **Cost is very low:** ~$0.002 per lecture
✅ **Current hybrid approach is optimal:** DeepSeek for TOC, Llama for content
✅ **Monthly cost for 100 lectures:** ~$0.20 (20 cents)

For academic/research use, this cost is negligible and worth it for the quality improvement!
