"""
LLM-generated Mermaid when PDF figures / captions are unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import List

from presentation.llm_response import pick_llm_text

logger = logging.getLogger(__name__)

_CHAR_REPLACEMENTS = (
    ("‑", "-"),
    ("–", "-"),
    ("—", "-"),
    ("·", "*"),
    ("×", "*"),
    ("φ", "phi"),
    ("Φ", "Phi"),
    ("⁻¹", "^-1"),
    ("⁻", "-"),
    ("…", "..."),
)


def sanitize_mermaid_for_cli(source: str) -> str:
    text = (source or "").strip()
    for old, new in _CHAR_REPLACEMENTS:
        text = text.replace(old, new)
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("thinking="):
            continue
        line = re.sub(
            r"(\w+)\[([^\]]+)\]",
            lambda m: _quote_label(m.group(1), m.group(2), "[]"),
            line,
        )
        line = re.sub(
            r"(\w+)\{([^}]+)\}",
            lambda m: _quote_label(m.group(1), m.group(2), "{}"),
            line,
        )
        lines.append(line)
    return "\n".join(lines).strip()


def _quote_label(node_id: str, label: str, kind: str) -> str:
    needs_quote = any(ch in label for ch in "()=/*^")
    if not needs_quote:
        if kind == "[]":
            return f"{node_id}[{label}]"
        return f"{node_id}{{{label}}}"
    safe = label.replace('"', "'").strip()
    if kind == "[]":
        return f'{node_id}["{safe}"]'
    return f'{node_id}{{"{safe}"}}'


def extract_mermaid_code(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "flowchart TD\n  A[Start] --> B[End]"
    # Ollama repr leak: response='flowchart TD\n ...'
    m = re.search(
        r"(?:response\s*=\s*['\"]|^)\s*(flowchart\s+TD[\s\S]*?)(?:['\"]\s*thinking|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        text = m.group(1)
    m2 = re.search(r"(flowchart\s+TD[\s\S]+)", text, re.IGNORECASE)
    if m2:
        text = m2.group(1)
    text = text.replace("\\n", "\n")
    text = re.sub(r"^```(?:mermaid)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    # Mermaid-cli is picky: replace special dashes and superscripts in labels
    text = text.replace("‑", "-").replace("⁻", "^-").replace("'", "'")
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("thinking="):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    if "flowchart" not in text.lower() and "graph" not in text.lower():
        text = "flowchart TD\n" + text
    text = text or "flowchart TD\n  A[Start] --> B[End]"
    return sanitize_mermaid_for_cli(text)


async def generate_mermaid_diagram(
    image_need: str,
    bullets: List[str],
    llm_generate,
) -> str:
    context = "\n".join(f"- {b}" for b in bullets[:6])
    prompt = f"""Составь диаграмму Mermaid (flowchart TD) для учебного слайда.
Верни ТОЛЬКО код Mermaid. Без markdown, без пояснений.
Тема: {image_need}

Контекст:
{context}

Правила: 5–8 узлов, короткие подписи, только flowchart TD, русский язык в узлах.
Без скобок () в подписях, без символов φ · ⁻ — используй phi, mod, умножение через *."""
    response = await llm_generate(
        prompt=prompt,
        options={"temperature": 0.2, "num_ctx": 4096},
    )
    raw = pick_llm_text(response)
    code = extract_mermaid_code(raw)
    logger.info("Mermaid diagram: %d lines", code.count("\n") + 1)
    return code
