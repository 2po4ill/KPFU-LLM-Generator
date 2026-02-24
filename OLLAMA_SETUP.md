# Ollama Setup Guide for KPFU LLM Generator

## Step 1: Install Ollama

### Windows Installation
1. Download Ollama from: https://ollama.com/download/windows
2. Run the installer (OllamaSetup.exe)
3. Ollama will install and start automatically

### Verify Installation
```bash
ollama --version
```

## Step 2: Download Llama 3.1 8B Model

This is the model specified in your design (optimal for Russian content, 4.7GB RAM):

```bash
ollama pull llama3.1:8b
```

This will download ~4.7GB. Wait for it to complete.

## Step 3: Test Ollama

```bash
ollama run llama3.1:8b "Привет! Расскажи о Python."
```

You should see a response in Russian.

## Step 4: Verify Ollama is Running

Ollama runs as a service on `http://localhost:11434`

Test with:
```bash
curl http://localhost:11434/api/tags
```

Or in PowerShell:
```powershell
Invoke-WebRequest -Uri http://localhost:11434/api/tags
```

## Step 5: Install Python Ollama Client

```bash
pip install ollama
```

## Alternative: Smaller Model for Testing

If 4.7GB is too large, you can use a smaller model:

```bash
# Llama 3.2 3B (2GB RAM)
ollama pull llama3.2:3b

# Or even smaller for testing
ollama pull phi3:mini
```

## Troubleshooting

### Ollama Not Starting
- Check Windows Services: Look for "Ollama" service
- Restart: `net stop ollama` then `net start ollama`

### Port Already in Use
- Ollama uses port 11434 by default
- Check if another service is using it

### Model Download Fails
- Check internet connection
- Try again - downloads can resume

## Next Steps

Once Ollama is installed and running:
1. Run: `python test_ollama_integration.py`
2. This will test the integration with your pipeline

## Memory Requirements

- **Llama 3.1 8B**: 4.7GB RAM (recommended)
- **System**: Additional 3GB for OS
- **Total**: 8GB RAM minimum

Your system should have at least 8GB RAM for comfortable operation.
