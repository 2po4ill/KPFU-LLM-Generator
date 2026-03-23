# What LLM Receives for TOC Page Selection

## Code Flow

### Step 1: Find TOC Pages
```python
# In generator_v2.py, _step1_smart_page_selection()
toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
# Returns: [3, 4, 5, 6, 7]
```

### Step 2: Extract Raw TOC Text
```python
# Get text from TOC pages
toc_text = '\n\n'.join([
    p['text'] for p in pages_data['pages'] 
    if p['page_number'] in toc_page_numbers
])

# Limit to 10000 chars
if len(toc_text) > 10000:
    toc_text = toc_text[:10000]
```

### Step 3: What the TOC Text Looks Like

Based on our earlier test (`test_toc_raw_text.py`), the TOC text from pages 3-7 looks like this:

```
Оглавление
1
Обложка
1
1.1
«Укус Питона» – «A Byte of Python» по-русски
. . . . . . . . . . . . . . . . .
1
1.2
Кто читает «A Byte of Python»? . . . . . . . . . . . . . . . . . . . . . . . . . . .
1
1.3
Лицензия . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
5
...
14 Объектно-ориентированное программирование
101
14.1
self . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
102
14.2
Классы
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
103
14.3
Методы
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
104
...
```

**Key Pattern**:
- Main chapter: `14 Объектно-ориентированное программирование` on one line, then `101` on next line
- Subsections: `14.1` on one line, `self` on next, dots, then `102` on next

### Step 4: The Prompt LLM Receives

```python
prompt = f"""Вот оглавление книги:

{toc_text}  # <-- The messy text above

Тема лекции: "Основы ООП: Классы, объекты, методы, наследование"

Найди в оглавлении разделы, которые относятся к этой теме, и верни НОМЕРА СТРАНИЦ (не номера разделов!).

ВАЖНО:
- Верни именно НОМЕРА СТРАНИЦ (обычно это большие числа типа 101, 102, 103)
- НЕ возвращай номера разделов (типа 14.1, 14.2)
- Если в книге НЕТ подходящих разделов, верни ТОЛЬКО: 0

Примеры:
- Если тема не подходит: 0
- Если тема подходит: 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112

Номера страниц (большие числа, не номера разделов):"""
```

### Step 5: What LLM Actually Returns

From the test output:
```
LLM page selection response: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8
```

## The Problem

The LLM sees this in the TOC:
```
14 Объектно-ориентированное программирование
101
14.1
self
...
102
14.2
Классы
...
103
```

**What it SHOULD return**: `101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112`

**What it ACTUALLY returns**: `14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8`

## Why This Happens

The LLM is confused by the format:
1. It sees "14.1" and "102" on different lines
2. It associates "14.1" with the section about OOP
3. It returns the section numbers instead of page numbers
4. Despite explicit instructions to return "big numbers like 101, 102"

## The Root Cause

The TOC format is ambiguous:
```
14.1          <-- Section number (what LLM returns)
self          <-- Section title
. . . . .     <-- Dots
102           <-- Page number (what we want)
```

The LLM can't reliably distinguish between:
- Section numbers (14.1, 14.2)
- Page numbers (102, 103)

Because they're on separate lines and the format is inconsistent.

## Possible Solutions

### Option 1: Give LLM More Context
Show actual example from THIS book:
```python
prompt = f"""Вот оглавление книги:

{toc_text}

Тема: "Основы ООП"

ПРИМЕР из этого оглавления:
Строка "14 Объектно-ориентированное программирование" → следующая строка "101" ← это номер страницы
Строка "14.1" → пропускаем → строка "self" → пропускаем → строка "102" ← это номер страницы

Найди все страницы для темы. Верни ТОЛЬКО большие числа (101, 102, 103...), НЕ маленькие (14.1, 14.2).

Номера страниц:"""
```

### Option 2: Post-Process LLM Response
```python
# If LLM returns section numbers, try to find corresponding pages
if all(n < 20 for n in page_numbers):  # All numbers are small (section numbers)
    # Parse TOC to map section numbers to page numbers
    # 14.1 → 102, 14.2 → 103, etc.
```

### Option 3: Use Regex (Reliable but Brittle)
Go back to regex parsing since we know the format:
```python
# Pattern: section number on one line, then skip lines, then page number
```

### Option 4: Hybrid Approach
1. Try LLM first
2. If response looks like section numbers (all < 20), fall back to regex
3. Use regex to map section numbers to page numbers

## Recommendation

Use **Option 4 (Hybrid)**: Try LLM, detect if it returned section numbers, then use regex to map them to actual page numbers.

This gives us:
- Flexibility of LLM (works with any book)
- Reliability of regex (when LLM fails)
