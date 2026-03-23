"""
Simple test bot to verify Telegram connection
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test start command"""
    await update.message.reply_text("✅ Bot is working! Connection successful.")
    logger.info(f"Received /start from user {update.effective_user.id}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo any message"""
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")
    logger.info(f"Echoed message: {text}")

def main():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return
    
    print(f"Starting bot with token: {token[:10]}...")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    
    print("✅ Bot started! Send /start in Telegram")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
