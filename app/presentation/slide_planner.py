"""
LLM: lecture markdown -> structured slides JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from presentation.sanitize import (
    is_noise_bullet,
    parse_concept_origin_pages,
    simplify_markdown_for_slide,
)

logger = logging.getLogger(__name__)

SLIDES_JSON_SCHEMA_HINT = """
Верни ТОЛЬКО JSON (без markdown-ограждений):
{
  "slides": [
    {
      "layout": "title",
      "title": "Тема лекции",
      "subtitle": "Дисциплина / курс"
    },
    {
      "layout": "content",
      "title": "Заголовок слайда",
      "bullets": [
        "Законченное предложение с мыслью, а не набор ключевых слов.",
        "Второе предложение раскрывает аспект темы."
      ],
      "speaker_notes": "кратко для преподавателя",
      "image": {
        "strategy": "none|mermaid|source",
        "image_need": "что должно быть на схеме (если нужна)",
        "image_caption": "краткое название рисунка на русском для подписи «Рис. N - …»",
        "source_pages": [20],
        "figure_hint": "Рис. 2.1",
        "mermaid": "flowchart TD\\n  A-->B"
      }
    }
  ]
}

Правила содержания (важно):
- Презентация — **выжимка лекции**: связные мысли для студента, а не перечень тегов и аббревиатур.
- На content-слайде **2–4 пункта**; каждый пункт — **законченное предложение** (12–22 слова), раскрывающее одну мысль.
- Не дроби одну мысль на «SQL‑инъекции», «XSS», «DDoS» без контекста — либо объедини в предложение, либо вынеси на отдельный слайд с пояснением.
- Большой раздел лекции → **2–3 слайда** с уточнением в заголовке: «… (часть 1)», «… (продолжение)».
- 10–18 content-слайдов + 1 title в начале (закрывающий титульный добавится автоматически).
- layout: только "title" или "content".

Правила иллюстраций:
- **image.strategy=none** — по умолчанию для большинства слайдов. Текстовый слайд без картинки — норма.
- **strategy=mermaid** — ТОЛЬКО если слайд про алгоритм, этапы процесса, kill chain, классификацию со стрелками; заполни mermaid (flowchart TD, 5–8 узлов) и **image_caption** (осмысленное название на русском, напр. «Этапы кибератаки»).
- **strategy=source** — ТОЛЬКО если в лекции явно нужен рисунок из учебника; укажи source_pages из блока «Источник» / CONCEPT_ORIGIN.
- **Не добавляй** иллюстрацию «для красоты». Если схема не нужна — strategy=none.
- image_caption — короткая подпись для студента (3–8 слов), не «mermaid diagram» и не «схема».
- Не выдумывай номера страниц.
"""


def _extract_page_hints(lecture_md: str) -> List[int]:
    pages = set()
    for m in re.finditer(r"(?:стр\.?|страниц[аы]?)\s*[:\s]*(\d{1,4})", lecture_md, re.I):
        pages.add(int(m.group(1)))
    for m in re.finditer(r"CONCEPT_ORIGIN[^\d]*(\d{1,4})", lecture_md, re.I):
        pages.add(int(m.group(1)))
    return sorted(pages)[:40]


def _truncate_lecture(lecture_md: str, max_chars: int = 14000) -> str:
    text = (lecture_md or "").strip()
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.65)]
    tail = text[-int(max_chars * 0.25) :]
    return head + "\n\n...[сокращено]...\n\n" + tail


def _looks_like_tag_bullet(text: str) -> bool:
    s = (text or "").strip()
    if len(s) < 8:
        return True
    words = s.split()
    if len(words) <= 3 and not re.search(r"[.!?;:]", s):
        return True
    if re.match(r"^[\w\-–—/]+(?:\s*[,;]\s*[\w\-–—/]+){0,4}$", s) and len(words) <= 5:
        return True
    return False


def _normalize_image_block(block: Optional[Dict[str, Any]], slide_title: str) -> Dict[str, Any]:
    img = dict(block or {})
    strategy = str(img.get("strategy") or "none").lower()
    if strategy not in ("none", "mermaid", "source"):
        strategy = "none"
    img["strategy"] = strategy
    if strategy == "none":
        return {"strategy": "none"}
    caption = str(img.get("image_caption") or img.get("image_need") or slide_title or "").strip()
    if caption.lower() in ("mermaid diagram", "mermaid", "схема", "диаграмма", "diagram"):
        caption = str(img.get("image_need") or slide_title or "").strip()
    if caption:
        img["image_caption"] = simplify_markdown_for_slide(caption, max_len=80)
    return img


def _normalize_content_slide(slide: Dict[str, Any], *, max_bullets: int, max_bullet_chars: int) -> Dict[str, Any]:
    out = dict(slide)
    title = simplify_markdown_for_slide(str(out.get("title") or "Слайд"), max_len=80)
    out["title"] = title
    raw_bullets = [str(b).strip() for b in (out.get("bullets") or []) if str(b).strip()]
    bullets: List[str] = []
    for b in raw_bullets:
        if is_noise_bullet(b):
            continue
        clean = simplify_markdown_for_slide(b, max_len=max_bullet_chars)
        if clean and clean not in bullets:
            bullets.append(clean)
    if len(bullets) == 1 and _looks_like_tag_bullet(bullets[0]):
        bullets = [bullets[0] + " — см. конспект лекции."]
    out["bullets"] = bullets[:12] or [
        simplify_markdown_for_slide(
            f"Ключевые положения раздела «{title}» изложены в конспекте лекции.",
            max_len=max_bullet_chars,
        )
    ]
    out["image"] = _normalize_image_block(
        out.get("image") if isinstance(out.get("image"), dict) else None,
        title,
    )
    cap = str(out.get("image_caption") or (out.get("image") or {}).get("image_caption") or "").strip()
    if cap:
        out["image_caption"] = simplify_markdown_for_slide(cap, max_len=80)
    return out


def _split_overflow_slide(slide: Dict[str, Any], *, max_bullets: int) -> List[Dict[str, Any]]:
    bullets = list(slide.get("bullets") or [])
    if len(bullets) <= max_bullets:
        return [slide]
    title = str(slide.get("title") or "Слайд")
    parts: List[Dict[str, Any]] = []
    chunk_size = max(2, max_bullets)
    for i in range(0, len(bullets), chunk_size):
        chunk = bullets[i : i + chunk_size]
        part_title = title if i == 0 else f"{title} (продолжение)"
        if i > 0 and "(часть" not in title and "(продолжение)" not in title:
            part_num = i // chunk_size + 1
            part_title = f"{title} (часть {part_num})"
        part = dict(slide)
        part["title"] = simplify_markdown_for_slide(part_title, max_len=80)
        part["bullets"] = chunk
        if i > 0:
            part["image"] = {"strategy": "none"}
            part.pop("image_caption", None)
        parts.append(part)
    return parts


def postprocess_slides(
    data: Dict[str, Any],
    *,
    max_content_slides: int = 18,
    max_bullets: int = 4,
    max_bullet_chars: int = 140,
) -> Dict[str, Any]:
    raw = list(data.get("slides") or [])
    out: List[Dict[str, Any]] = []
    content_count = 0
    for slide in raw:
        layout = str(slide.get("layout") or "content").lower()
        if layout == "title":
            out.append(slide)
            continue
        if content_count >= max_content_slides:
            break
        norm = _normalize_content_slide(
            slide,
            max_bullets=max_bullets,
            max_bullet_chars=max_bullet_chars,
        )
        for part in _split_overflow_slide(norm, max_bullets=max_bullets):
            if content_count >= max_content_slides:
                break
            out.append(part)
            content_count += 1
    if not any(str(s.get("layout") or "").lower() == "title" for s in out):
        out.insert(0, {"layout": "title", "title": "Лекция", "subtitle": ""})
    return {"slides": out}


def parse_slides_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        fixed = text.replace("'", '"')
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        data = json.loads(fixed)
    if not isinstance(data, dict) or "slides" not in data:
        raise ValueError("JSON must contain 'slides' array")
    if not isinstance(data["slides"], list):
        raise ValueError("'slides' must be a list")
    return data


async def plan_slides_from_lecture(
    *,
    theme: str,
    lecture_md: str,
    subject_title: str,
    llm_generate,
    max_slides: int = 18,
    max_bullets: int = 4,
    max_bullet_chars: int = 140,
) -> Dict[str, Any]:
    """
    llm_generate: async callable(prompt, options) -> dict with 'response' and optional 'thinking'.
    """
    page_hints = _extract_page_hints(lecture_md)
    lecture_body = _truncate_lecture(lecture_md)
    prompt = f"""Ты готовишь презентацию PowerPoint по готовой лекции для студентов бакалавриата.
Тема: {theme}
Дисциплина: {subject_title or '—'}
Известные номера страниц источника (подсказка): {page_hints or 'не указаны'}

Лекция:
{lecture_body}

{SLIDES_JSON_SCHEMA_HINT}
Максимум content-слайдов: {max_slides}.
"""
    response = await llm_generate(
        prompt=prompt,
        options={"temperature": 0.25, "num_ctx": 8192},
    )
    from presentation.llm_response import pick_llm_text

    raw = pick_llm_text(response)
    try:
        data = parse_slides_json(raw)
    except Exception as e:
        logger.warning("slides JSON parse failed: %s; using fallback outline", e)
        data = _fallback_slides_from_markdown(theme, lecture_md, subject_title, max_slides)
    return postprocess_slides(
        data,
        max_content_slides=max_slides,
        max_bullets=max_bullets,
        max_bullet_chars=max_bullet_chars,
    )


def _paragraphs_from_section(sec: str, *, max_items: int = 4, max_len: int = 140) -> List[str]:
    lines = [ln.strip() for ln in sec.strip().splitlines() if ln.strip()]
    bullets: List[str] = []
    buf: List[str] = []
    for ln in lines[1:]:
        if ln.startswith("#") or is_noise_bullet(ln):
            if buf:
                bullets.append(simplify_markdown_for_slide(" ".join(buf), max_len=max_len))
                buf = []
            continue
        if ln.startswith(("-", "*")):
            if buf:
                bullets.append(simplify_markdown_for_slide(" ".join(buf), max_len=max_len))
                buf = []
            bullets.append(
                simplify_markdown_for_slide(re.sub(r"^[-*]\s*", "", ln), max_len=max_len)
            )
        elif re.match(r"^\d+\.", ln):
            if buf:
                bullets.append(simplify_markdown_for_slide(" ".join(buf), max_len=max_len))
                buf = []
            bullets.append(simplify_markdown_for_slide(re.sub(r"^\d+\.\s*", "", ln), max_len=max_len))
        elif len(ln) > 25:
            buf.append(ln)
        if len(bullets) >= max_items * 2:
            break
    if buf:
        bullets.append(simplify_markdown_for_slide(" ".join(buf), max_len=max_len))
    return [b for b in bullets if b and not is_noise_bullet(b)]


def _fallback_slides_from_markdown(
    theme: str,
    lecture_md: str,
    subject_title: str,
    max_slides: int,
) -> Dict[str, Any]:
    slides: List[Dict[str, Any]] = [
        {
            "layout": "title",
            "title": theme,
            "subtitle": subject_title or "",
        }
    ]
    parts = re.split(r"\n###\s+", lecture_md)
    if len(parts) > 2:
        sections = parts[1 : max_slides + 1]
        section_mode = "h3"
    else:
        sections = re.split(r"\n##\s+", lecture_md)[1 : max_slides + 1]
        section_mode = "h2"
    for sec in sections:
        lines = [ln.strip() for ln in sec.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("#").strip()
        if section_mode == "h2" and title.lower() in {"основные концепции", "основные понятия"}:
            inner = re.split(r"\n###\s+", sec, maxsplit=1)
            if len(inner) > 1:
                sec = inner[1]
                lines = [ln.strip() for ln in sec.strip().splitlines() if ln.strip()]
                if lines:
                    title = lines[0].lstrip("#").strip()
        bullets = _paragraphs_from_section(sec, max_items=4)
        if not bullets:
            continue
        slide_base = {
            "layout": "content",
            "title": simplify_markdown_for_slide(title, max_len=80),
            "bullets": bullets,
            "image": {"strategy": "none"},
        }
        for part in _split_overflow_slide(slide_base, max_bullets=4):
            slides.append(part)
            if len(slides) > max_slides + 1:
                break
        if len(slides) > max_slides + 1:
            break
    return {"slides": slides}
