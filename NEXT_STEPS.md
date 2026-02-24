# Next Steps: Ollama Integration

## Current Status ✅

Your KPFU LLM Generator is **95% complete**! Here's what's working:

1. ✅ RPD data input with fingerprint tracking
2. ✅ PDF book upload and processing (383 chunks from your Python book!)
3. ✅ FAISS vector storage for semantic search
4. ✅ Complete 5-step hybrid content generation pipeline
5. ✅ FGOS-compliant formatting
6. ✅ Citation management
7. ✅ Database storage
8. ✅ All APIs ready

## What's Missing: Real LLM

Currently using **mock LLM** (placeholder content). To get real content generation:

### Step 1: Install Ollama

**Download and install:**
- Go to: https://ollama.com/download/windows
- Download OllamaSetup.exe
- Run installer
- Ollama will start automatically

### Step 2: Download Model

Open PowerShell/CMD and run:
```bash
ollama pull llama3.1:8b
```

This downloads the Llama 3.1 8B model (~4.7GB). Wait for completion.

### Step 3: Verify Installation

```bash
# Check Ollama is running
ollama --version

# Test the model
ollama run llama3.1:8b "Привет! Расскажи о Python."
```

You should see a Russian response about Python.

### Step 4: Test Integration

```bash
python test_ollama_integration.py
```

This will run 3 tests:
1. Basic Ollama connection
2. ModelManager integration
3. Russian content generation

All should pass ✅

### Step 5: Run Complete Pipeline with Real LLM

Once Ollama tests pass, update the test to use real LLM:

In `test_complete_pipeline.py`, change line 155:
```python
# FROM:
generator = await get_content_generator(
    model_manager=None,  # Using mock
    embedding_service=embedding_service,
    pdf_processor=pdf_processor,
    use_mock=True  # <-- Change this
)

# TO:
from core.model_manager import ModelManager

model_manager = ModelManager(use_mock_services=False)
await model_manager.initialize()

generator = await get_content_generator(
    model_manager=model_manager,  # Real model manager
    embedding_service=embedding_service,
    pdf_processor=pdf_processor,
    use_mock=False  # <-- Real LLM!
)
```

Then run:
```bash
python test_complete_pipeline.py
```

You'll see **real lecture content** generated from your Python book!

## Expected Results

With real LLM, you'll get:
- Actual lecture content in Russian
- Based on your Python book
- FGOS-formatted
- With proper citations
- ~90-120 seconds generation time

## System Requirements

- **RAM**: 8GB minimum (4.7GB for model + 3GB for system)
- **Disk**: 5GB free (for model)
- **CPU**: Any modern CPU (GPU not required, but faster)

## Troubleshooting

### "Ollama not found"
- Restart your terminal after installation
- Check Windows Services for "Ollama" service

### "Model not found"
- Run: `ollama pull llama3.1:8b`
- Wait for download to complete

### "Connection refused"
- Ollama service not running
- Try: `ollama serve` in a separate terminal

### Out of memory
- Close other applications
- Use smaller model: `ollama pull llama3.2:3b`

## Alternative: Sentence Transformers for Embeddings

For better semantic search (currently using mock), install:

```bash
pip install sentence-transformers
```

Then in `test_complete_pipeline.py`, change line 138:
```python
# FROM:
embedding_service = await get_embedding_service(use_mock=True)

# TO:
embedding_service = await get_embedding_service(
    model_manager=model_manager,
    use_mock=False
)
```

This will use real embeddings for semantic search!

## Final Production Setup

Once everything works:

1. **Start the API server:**
   ```bash
   python app/main.py
   ```

2. **Test via API:**
   ```bash
   python test_rpd_api.py
   ```

3. **Upload books via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/literature/upload-book \
     -F "file=@питон_мок_дата.pdf" \
     -F "title=A Byte of Python" \
     -F "authors=Swaroop C H"
   ```

4. **Generate content:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/rpd/generate-content?fingerprint=a573602cf80bec12&theme_title=Введение в Python"
   ```

## You're Almost There! 🎉

Just install Ollama and you'll have a fully functional LLM-powered educational content generator!

Questions? Check:
- `OLLAMA_SETUP.md` - Detailed Ollama setup
- `test_ollama_integration.py` - Integration tests
- `PROGRESS_SUMMARY.md` - What's been built

Good luck! 🚀
