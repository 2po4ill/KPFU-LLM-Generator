# Prompt for AI Diagram Generator

Create a professional software architecture diagram for an LLM-based educational content generation system with the following structure:

## Overall Layout
- **Direction**: Top-to-bottom hierarchical layout
- **Style**: Modern, clean, professional software architecture diagram
- **Color scheme**: Use distinct colors for different layers with good contrast

## Architecture Layers (3 main layers)

### 1. Top Level: FastAPI Application
- Main application node: "FastAPI Application (app/main.py)"
- Color: Dark blue (#2C3E50)
- This connects to all three layers below

### 2. Three Main Layers (same level, side by side):

#### Layer A: API Layer (app/api/)
- Color: Blue (#3498DB)
- Contains 3 modules:
  - routes.py (Основные эндпоинты)
  - literature_routes.py (Работа с литературой)
  - rpd_routes.py (Обработка РПД)

#### Layer B: Core Layer (app/core/)
- Color: Orange (#E67E22)
- Contains 4 modules:
  - config.py (Конфигурация)
  - database.py (База данных)
  - cache.py (Кэширование)
  - model_manager.py (Управление LLM)

#### Layer C: Domain Layer (Бизнес-логика)
- Color: Green (#27AE60)
- Contains 5 sub-modules (each in its own group):

**Literature Module (app/literature/)**
- processor.py (Обработка PDF, TOC, offset)
- embeddings.py (Векторизация)

**Generation Module (app/generation/)**
- generator_v3.py (Многофазная генерация с батчингом)

**RPD Module (app/rpd/)**
- extractor.py (Извлечение данных)
- parsers.py (Парсинг структуры)
- processor.py (Обработка)

**Bot Module (app/bot/)**
- telegram_bot.py (Telegram интерфейс)

## Connections (arrows)

### Solid arrows (main architectural flow):
- FastAPI Application → API Layer
- FastAPI Application → Core Layer
- FastAPI Application → Domain Layer
- API Layer → its 3 modules
- Core Layer → its 4 modules
- Domain Layer → all 5 sub-modules
- Each sub-module → its files

### Dashed arrows (cross-module dependencies):
- literature_routes.py → processor.py (Literature)
- literature_routes.py → generator_v3.py
- rpd_routes.py → processor.py (RPD)
- generator_v3.py → model_manager.py
- processor.py (Literature) → cache.py
- telegram_bot.py → literature_routes.py

## Visual Requirements
- Use rounded rectangles for all nodes
- Make module groups visually distinct with borders
- Use white text on dark backgrounds
- Use black text on light backgrounds
- Add subtle shadows for depth
- Ensure all text is readable
- Make the diagram suitable for academic/technical documentation

## Export Format
- High resolution PNG (300 DPI minimum)
- Transparent or white background
- Size: suitable for A4 document (landscape orientation preferred)

---

## Alternative Simplified Description

If the above is too complex, create a hierarchical diagram showing:
1. Top: FastAPI App
2. Second level: 3 boxes (API, Core, Domain)
3. Third level: Show key modules under each
4. Use arrows to show main data flow
5. Professional colors and clean layout
