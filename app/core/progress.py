"""Generation progress events for SSE / UI hotbar."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

ProgressCallback = Callable[[Dict[str, Any]], None]

# Canonical step ids for UI
STEPS_PACKAGE = [
    ("init", "Старт"),
    ("step1_user_sources", "Приоритетные источники"),
    ("step1_pages", "Подбор страниц учебника"),
    ("step2_rag", "Извлечение фрагментов (RAG)"),
    ("step2_facets", "Генерация разделов лекции"),
    ("step2_lab", "Лабораторная работа"),
    ("step2_selfcheck", "Самопроверка"),
    ("step3_validate", "Проверка по источникам"),
    ("step3_pptx", "Презентация (слайды и картинки)"),
    ("done", "Готово"),
]


def progress_event(
    step_id: str,
    message: str,
    *,
    detail: str = "",
    status: str = "active",
    pct: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "step_id": step_id,
        "message": message,
        "detail": detail,
        "status": status,
        "pct": pct,
        "ts": time.time(),
    }
