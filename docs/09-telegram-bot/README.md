# Telegram Bot Interface

**Status**: ✅ Ready for Presentation  
**Purpose**: Simple UI for course generation demonstration

---

## 🎯 Quick Start

### 1. Get Bot Token

1. Open Telegram, find @BotFather
2. Send `/newbot`
3. Name: "KPFU Course Generator"
4. Username: "kpfu_course_gen_bot"
5. Copy token

### 2. Configure

Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_token_here
```

### 3. Install Dependencies

```bash
pip install python-telegram-bot==20.7
```

### 4. Run Bot

**Windows**:
```bash
run_telegram_bot.bat
```

**Linux/Mac**:
```bash
chmod +x run_telegram_bot.sh
./run_telegram_bot.sh
```

**Or directly**:
```bash
python app/bot/telegram_bot.py
```

---

## 💬 How to Use

### Step 1: Start
Send `/start` to bot

### Step 2: Enter Information
- Направление подготовки: "Программная инженерия"
- Уровень: Select "Бакалавриат"
- Кафедра: "Кафедра ИВТ"

### Step 3: Upload Books
- Send 1-3 PDF files
- Type "готово" when done

### Step 4: Enter Themes
```
Введение в Python
Работа со строками
Списки и кортежи
```

### Step 5: Confirm
Type "да" to start generation

### Step 6: Receive Lectures
Bot will send each lecture as it's generated

---

## 📊 Features

### Current Features
- ✅ Conversational interface
- ✅ PDF book upload
- ✅ Multi-book support
- ✅ Real-time progress updates
- ✅ Automatic file delivery
- ✅ Generation statistics

### User Experience
- Simple step-by-step flow
- Clear instructions
- Progress notifications
- Immediate file delivery
- Error handling

---

## 🎓 Example Session

```
User: /start

Bot: 🎓 Генератор учебных материалов КПФУ
     Добро пожаловать!
     📝 Направление подготовки:

User: Программная инженерия

Bot: ✓ Направление: Программная инженерия
     📚 Уровень образования:
     [Бакалавриат] [Магистратура] [Аспирантура]

User: [Clicks Бакалавриат]

Bot: ✓ Уровень: Бакалавриат
     🏛️ Кафедра:

User: Кафедра информационных систем

Bot: ✓ Кафедра: Кафедра информационных систем
     📚 Загрузка учебников:
     Отправьте PDF файлы

User: [Uploads 3 PDF files]
User: готово

Bot: ✓ Загружено книг: 3
     📝 Темы лекций:

User: Введение в Python
      Работа со строками
      Списки и кортежи

Bot: 📋 Сводка курса:
     Направление: Программная инженерия
     Уровень: Бакалавриат
     Кафедра: Кафедра информационных систем
     Книг: 3
     Лекций: 3
     ⏱️ Примерное время: 10 минут
     Начать генерацию? (да/нет)

User: да

Bot: 🚀 Начинаю генерацию курса...
     📚 Инициализация книг...
     ✓ Книги инициализированы
     📝 Генерация лекции 1/3: Введение в Python
     ✓ Лекция 1 готова: 1,861 слов, 198.3с
     📄 [Sends lecture file]
     ...
     ✅ Генерация завершена!
     Статистика: 3 лекции, 8,823 слова, 10 минут
```

---

## 🔧 Technical Details

### Architecture
```
Telegram Bot (telegram_bot.py)
    ↓
Generator V3 (generator_v3.py)
    ↓
Model Manager (model_manager.py)
    ↓
Ollama (llama3.1:8b)
```

### File Structure
```
app/bot/
├── __init__.py
└── telegram_bot.py          # Main bot code

docs/09-telegram-bot/
├── README.md                # This file
└── TELEGRAM_BOT_SETUP.md    # Detailed setup

run_telegram_bot.bat         # Windows launcher
run_telegram_bot.sh          # Linux/Mac launcher
```

### Dependencies
- python-telegram-bot==20.7
- All existing project dependencies

---

## 📝 Documentation

- [Detailed Setup Guide](./TELEGRAM_BOT_SETUP.md)
- [Bot Code](../../app/bot/telegram_bot.py)
- [Generator V3 Architecture](../../GENERATOR_V3_FINAL_ARCHITECTURE.md)

---

## 🚀 For Presentation

### Demo Script

1. **Show Bot Start**
   - Open Telegram
   - Send `/start`
   - Show welcome message

2. **Enter Course Info**
   - Направление: "Программная инженерия"
   - Уровень: "Бакалавриат"
   - Кафедра: "Кафедра ИВТ"

3. **Upload Books**
   - Upload 2-3 PDF files
   - Show upload confirmation
   - Type "готово"

4. **Enter Themes**
   - Enter 3 lecture themes
   - Show summary

5. **Start Generation**
   - Confirm with "да"
   - Show progress updates
   - Receive generated lectures

6. **Show Results**
   - Open generated lecture files
   - Show quality and structure
   - Show statistics

### Key Points to Highlight

- ✅ Simple, conversational interface
- ✅ No technical knowledge required
- ✅ Real-time progress updates
- ✅ Automatic file delivery
- ✅ High-quality output (82.4% accuracy)
- ✅ Fast generation (~3 min per lecture)
- ✅ Multi-book synthesis
- ✅ FGOS compliance

---

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check if bot is running
ps aux | grep telegram_bot

# Check logs
tail -f bot.log
```

### Token Issues
- Verify token in .env
- Check token with @BotFather
- Regenerate if needed

### Generation Errors
- Ensure Ollama is running
- Check GPU availability
- Verify books are valid PDFs

---

## 🎯 Next Steps

### After Presentation
1. Gather feedback
2. Identify improvements
3. Add requested features
4. Deploy to production

### Future Features
- User authentication
- Generation queue
- Progress bar
- Cancel generation
- Lab manual generation
- SCORM export

---

**Document Version**: 1.0  
**Last Updated**: February 26, 2026  
**Status**: ✅ Ready for Presentation
