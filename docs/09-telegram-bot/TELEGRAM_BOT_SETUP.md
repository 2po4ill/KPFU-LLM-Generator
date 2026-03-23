# Telegram Bot Setup Guide

**Purpose**: Simple UI for course generation demonstration  
**Target**: Presentation and user testing

---

## 🎯 Overview

The Telegram Bot provides a simple, conversational interface for generating courses. Perfect for demonstrations and non-technical users.

### User Flow
```
/start
  ↓
Enter Направление подготовки
  ↓
Select Уровень образования (Бакалавриат/Магистратура/Аспирантура)
  ↓
Enter Кафедра name
  ↓
Upload PDF books (1-3 files)
  ↓
Enter lecture themes (one per line)
  ↓
Confirm and generate
  ↓
Receive generated lectures
```

---

## 📋 Prerequisites

### 1. Create Telegram Bot

1. Open Telegram and find @BotFather
2. Send `/newbot`
3. Choose bot name: "KPFU Course Generator"
4. Choose username: "kpfu_course_gen_bot" (or similar)
5. Copy the bot token

### 2. Install Dependencies

```bash
pip install python-telegram-bot==20.7
```

Or add to `requirements.txt`:
```
python-telegram-bot==20.7
```

### 3. Configure Environment

Add to `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

---

## 🚀 Running the Bot

### Method 1: Direct Run

```bash
python app/bot/telegram_bot.py
```

### Method 2: As Service

```bash
# Create systemd service (Linux)
sudo nano /etc/systemd/system/kpfu-bot.service
```

```ini
[Unit]
Description=KPFU Course Generator Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/kpfu-llm-generator
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python app/bot/telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable kpfu-bot
sudo systemctl start kpfu-bot
sudo systemctl status kpfu-bot
```

---

## 💬 Bot Commands

### User Commands
- `/start` - Start new course generation
- `/cancel` - Cancel current operation

### Admin Commands (future)
- `/stats` - Show generation statistics
- `/users` - List active users
- `/help` - Show help message

---

## 🎨 Bot Interface

### Welcome Message
```
🎓 Генератор учебных материалов КПФУ

Добро пожаловать! Я помогу создать полный курс лекций.

Давайте начнем с основной информации.

📝 Направление подготовки:
Например: Программная инженерия, Информатика и вычислительная техника
```

### Degree Selection
```
✓ Направление: Программная инженерия

📚 Уровень образования:
Выберите уровень подготовки:

[Бакалавриат] [Магистратура]
[Аспирантура]
```

### Book Upload
```
✓ Кафедра: Кафедра информационных систем

📚 Загрузка учебников:

Отправьте PDF файлы учебников (1-3 книги).
После загрузки всех книг напишите: готово
```

### Themes Input
```
✓ Загружено книг: 3

📝 Темы лекций:

Введите темы лекций (каждая тема с новой строки):

Пример:
Введение в Python
Работа со строками
Списки и кортежи
```

### Confirmation
```
📋 Сводка курса:

Направление: Программная инженерия
Уровень: Бакалавриат
Кафедра: Кафедра информационных систем
Книг: 3
Лекций: 12

Темы лекций:
1. Введение в Python
2. Основы синтаксиса и переменные
...

⏱️ Примерное время генерации: 40 минут

Начать генерацию? (да/нет)
```

### Generation Progress
```
🚀 Начинаю генерацию курса...

📚 Инициализация книг...
✓ Книги инициализированы

📝 Генерация лекции 1/12: Введение в Python
✓ Лекция 1 готова: 1,861 слов, 198.3с

📄 [Lecture file sent]

📝 Генерация лекции 2/12: Основы синтаксиса...
...
```

### Completion
```
✅ Генерация завершена!

Статистика:
- Лекций: 12
- Всего слов: 25,565
- Время генерации: 2,376.0с (39.6 мин)
- Среднее время: 198.0с на лекцию

Качество:
- Архитектура: Generator V3
- Точность: 82.4% (проверено)
- Соответствие ФГОС: ✓

Спасибо за использование! 🎓
```

---

## 🔧 Configuration

### Bot Settings

```python
# app/bot/telegram_bot.py

# Conversation states
PROFESSION = 0
DEGREE = 1
DEPARTMENT = 2
UPLOAD_BOOKS = 3
THEMES = 4
CONFIRM = 5
GENERATING = 6

# Limits
MAX_BOOKS = 3
MAX_THEMES = 20
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

### Customization

```python
# Change welcome message
async def start(self, update, context):
    await update.message.reply_text(
        "Your custom welcome message here"
    )

# Change degree options
keyboard = [
    ['Бакалавриат', 'Магистратура'],
    ['Аспирантура', 'Другое']
]

# Change generation parameters
result = await self.generator.generate_lecture_optimized(
    theme=theme,
    book_ids=book_ids,
    rpd_data={...},
    # Add custom parameters here
)
```

---

## 📊 Monitoring

### Logs

```bash
# View bot logs
tail -f bot.log

# View systemd logs
journalctl -u kpfu-bot -f
```

### Metrics

```python
# Track in code
logger.info(f"User {user_id} started generation")
logger.info(f"Generated {len(lectures)} lectures in {total_time}s")
logger.info(f"Average: {avg_time}s per lecture")
```

---

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check if bot is running
ps aux | grep telegram_bot

# Check logs
tail -f bot.log

# Restart bot
sudo systemctl restart kpfu-bot
```

### File Upload Issues
- Check file size limit (50MB default)
- Verify PDF format
- Check disk space

### Generation Errors
- Verify Ollama is running
- Check GPU availability
- Review model_manager logs
- Verify book initialization

---

## 🚀 Deployment

### Production Checklist
- [ ] Bot token secured in .env
- [ ] Systemd service configured
- [ ] Logs rotation set up
- [ ] Monitoring enabled
- [ ] Error notifications configured
- [ ] Backup strategy in place

### Security
- Keep bot token secret
- Validate all user inputs
- Limit file sizes
- Rate limit requests
- Monitor for abuse

---

## 📝 Future Enhancements

### Phase 1 (Current)
- [x] Basic conversation flow
- [x] Book upload
- [x] Lecture generation
- [x] File delivery

### Phase 2 (Future)
- [ ] User authentication
- [ ] Generation queue
- [ ] Progress bar
- [ ] Cancel generation
- [ ] Edit parameters

### Phase 3 (Future)
- [ ] Lab manual generation
- [ ] Assessment generation
- [ ] SCORM export
- [ ] Course preview
- [ ] Sharing capabilities

---

## 🎓 Usage Examples

### Example 1: Python Course
```
Направление: Программная инженерия
Уровень: Бакалавриат
Кафедра: Кафедра ИВТ
Книги: 3 PDF files
Темы: 12 lectures
Result: 12 lectures, 25,565 words, 40 minutes
```

### Example 2: Quick Demo
```
Направление: Информатика
Уровень: Магистратура
Кафедра: Кафедра ИС
Книги: 1 PDF file
Темы: 3 lectures
Result: 3 lectures, 8,823 words, 10 minutes
```

---

**Document Version**: 1.0  
**Last Updated**: February 26, 2026  
**Status**: Ready for Use
