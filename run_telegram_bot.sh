#!/bin/bash
# Run Telegram Bot for KPFU Course Generator

echo "========================================"
echo "KPFU Course Generator - Telegram Bot"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env file with TELEGRAM_BOT_TOKEN"
    echo ""
    echo "Example:"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    exit 1
fi

# Check if Ollama is running
echo "Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "WARNING: Ollama is not running!"
    echo "Please start Ollama first: ollama serve"
    echo ""
    read -p "Press Enter to continue anyway..."
fi

echo "Starting Telegram Bot..."
echo ""
python app/bot/telegram_bot.py
