# TOC Context Limit Issue

## Problem Discovery

When testing full TOC prompt in Ollama app, Llama:
1. Returned all odd numbers (1, 3, 5, 7, 9... 137)
2. Claimed they were "prime numbers" (incorrect)
3. Admitted it didn't see the TOC: "Нет, вы не отправляли мне никакого оглавления"
4. Said character limit was "20 characters" (confused)

**Root Cause:** The full TOC (~8000+ chars) exceeds Llama's context window or there's a prompt length limit in Ollama app.

## Solutions

### Option 1: Split TOC into Chunks
Send only relevant sections of TOC (e.g., chapters 7-14 for programming topics)

### Option 2: Pre-filter TOC with Keywords
Extract only lines containing keywords related to theme before sending to LLM

### Option 3: Use Structured Format
Convert TOC to simple list format:
```
7.4 Строки → 36
12.8 Ещё о строках → 89
```

### Option 4: Two-Stage Selection
1. First pass: Ask LLM which CHAPTERS are relevant (short prompt)
2. Second pass: Send only those chapters' sections for page selection

## Recommended Approach

**Two-Stage Selection** (Option 4):

Stage 1: Chapter-level filtering
```
Chapters:
7. Основы (35-44)
8. Операторы и выражения (45-50)
12. Структуры данных (79-90)
14. ООП (101-112)

Theme: Работа со строками
Which chapters? Return numbers only: 7, 12
```

Stage 2: Page-level selection
```
Chapter 7 sections:
7.4 Строки → 36
7.5 Переменные → 39

Chapter 12 sections:
12.8 Ещё о строках → 89

Return page numbers: 36, 89
```

This keeps each prompt under 1000 chars and gives LLM manageable context.
