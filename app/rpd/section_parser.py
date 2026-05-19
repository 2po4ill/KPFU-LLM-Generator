"""
Rule-based parsing of standard KPFU RPD sections (4.2 themes, FOS header block).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_section_42_content(text: str) -> str:
    """Text block for section 4.2 «Содержание дисциплины (модуля)»."""
    if not text:
        return ""
    m = re.search(
        r"4\.2\s*Содержание\s+дисциплины\s*(?:\(модуля\))?\s*\n?(.*?)"
        r"(?=\n\s*4\.3\s|\n\s*5\.\s|\nФонд\s+оценочных|\n\s*Раздел\s+\d|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    # Fallback: any «Содержание дисциплины» block
    m2 = re.search(
        r"Содержание\s+дисциплины\s*(?:\(модуля\))?\s*\n?(.*?)"
        r"(?=\n\s*4\.3\s|\nФонд\s+оценочных|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return m2.group(1).strip() if m2 else ""


def parse_lecture_themes_from_section_42(text: str) -> List[Dict[str, Any]]:
    """
    Parse «Тема N. …» blocks with sub-items N.M from section 4.2.
    Returns list of {title, order, hours, description}.
    """
    section = extract_section_42_content(text)
    if not section:
        return []

    themes: List[Dict[str, Any]] = []
    chunks = re.split(r"(?=Тема\s+\d+\s*\.)", section, flags=re.IGNORECASE)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        head = re.match(
            r"Тема\s+(\d+)\s*\.\s*(.+)",
            chunk,
            re.IGNORECASE | re.DOTALL,
        )
        if not head:
            continue
        order = int(head.group(1))
        body = head.group(2).strip()
        sub_start = re.search(r"(?:^|\s)(\d+\.\d+)\s*[\.\)]?\s*", body)
        if sub_start:
            title_part = body[: sub_start.start()].strip().rstrip(".")
            subs_part = body[sub_start.start() :].strip()
        else:
            title_part = _norm_ws(body.split("\n", 1)[0]).rstrip(".")
            subs_part = ""

        title = _norm_ws(title_part) or f"Тема {order}"
        subtopics: List[Dict[str, str]] = []
        sub_items: List[str] = []
        for sm in re.finditer(
            r"(\d+\.\d+)\s*[\.\)]?\s*([^0-9]+?)(?=\s*\d+\.\d+\s*[\.\)]|\s*Тема\s+\d+|\Z)",
            subs_part,
            re.IGNORECASE | re.DOTALL,
        ):
            code = sm.group(1).strip()
            sub_title = _norm_ws(sm.group(2)).rstrip(".")
            subtopics.append({"code": code, "title": sub_title})
            sub_items.append(f"{code} {sub_title}")

        description = "\n".join(sub_items) if sub_items else None
        themes.append(
            {
                "title": f"Тема {order}. {title}",
                "order": order,
                "hours": 2.0,
                "description": description,
                "subtopics": subtopics,
            }
        )

    themes.sort(key=lambda t: t["order"])
    return themes


def _is_numbered_toc_line(line: str) -> bool:
    return bool(re.match(r"^\d+\.\s+\S", (line or "").strip()))


def _find_fos_metadata_block(text: str) -> str:
    """Pick FOS block that contains direction/qualification (not TOC-only mention)."""
    chunks: List[str] = []
    for m in re.finditer(r"Фонд\s+оценочных\s+средств[^\n]*", text, re.IGNORECASE):
        chunks.append(text[m.start() : m.start() + 3500])
    for chunk in chunks:
        if re.search(r"Направление\s+подготовки", chunk, re.IGNORECASE):
            return chunk
    m = re.search(
        r"([^\n]{3,120})\n\s*Направление\s+подготовки\s*[:\-–]?\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if m and not _is_numbered_toc_line(m.group(1)):
        return m.group(0)
    return chunks[0] if chunks else text[:12000]


def parse_fos_header_block(text: str) -> Dict[str, Any]:
    """
    Parse metadata from «Фонд оценочных средств по дисциплине (модулю)» block.
    """
    out: Dict[str, Any] = {
        "subject_title": "",
        "profession": "",
        "academic_degree": "bachelor",
        "study_form": "",
        "language": "",
        "year": None,
        "profile": "",
    }
    if not text:
        return out

    block = _find_fos_metadata_block(text)

    def _field(label: str) -> Optional[str]:
        m = re.search(
            rf"{label}\s*[:\-–]?\s*([^\n]+)",
            block,
            re.IGNORECASE,
        )
        return _norm_ws(m.group(1)) if m else None

    direction = _field(r"Направление\s+подготовки")
    if direction:
        out["profession"] = direction

    qual = _field(r"Квалификация\s+выпускника")
    if qual:
        q = qual.lower()
        if "магистр" in q:
            out["academic_degree"] = "master"
        elif "аспирант" in q or "доктор" in q:
            out["academic_degree"] = "phd"
        else:
            out["academic_degree"] = "bachelor"

    form = _field(r"Форма\s+обучения")
    if form:
        out["study_form"] = form

    lang = _field(r"Язык\s+обучения")
    if lang:
        out["language"] = lang

    profile = _field(r"Профиль\s+подготовки")
    if profile:
        out["profile"] = profile

    year_m = re.search(
        r"Год\s+начала\s+обучения[^\n]*[:\-–]?\s*(\d{4})",
        block,
        re.IGNORECASE,
    )
    if year_m:
        out["year"] = int(year_m.group(1))

    # Discipline: line before «Направление подготовки» or first valid line after FOS header
    m_disc = re.search(
        r"Фонд\s+оценочных\s+средств[^\n]*\n\s*([^\n]+)\n\s*Направление\s+подготовки",
        block,
        re.IGNORECASE,
    )
    if m_disc:
        cand = _norm_ws(m_disc.group(1))
        if cand and not _is_numbered_toc_line(cand) and "Фонд оценочных" not in cand:
            out["subject_title"] = cand

    if not out["subject_title"]:
        for ln in block.splitlines():
            ln = ln.strip()
            if not ln or len(ln) < 3 or _is_numbered_toc_line(ln):
                continue
            if re.match(
                r"^(Направление|Квалификация|Форма|Профиль|Язык|Год|Фонд)\b",
                ln,
                re.IGNORECASE,
            ):
                continue
            out["subject_title"] = ln
            break

    if not out["subject_title"]:
        m = re.search(
            r"дисциплин[аы]\s*\(модуля\)\s*\n\s*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            out["subject_title"] = _norm_ws(m.group(1))

    return out


def parse_rpd_sections(raw_text: str) -> Dict[str, Any]:
    """Combined structured parse for RPD upload pipeline."""
    themes = parse_lecture_themes_from_section_42(raw_text)
    fos = parse_fos_header_block(raw_text)
    basic: Dict[str, Any] = {
        "subject_title": fos.get("subject_title") or "",
        "academic_degree": fos.get("academic_degree") or "bachelor",
        "profession": fos.get("profession") or "",
        "total_hours": 0,
        "year": fos.get("year"),
        "study_form": fos.get("study_form"),
        "language": fos.get("language"),
        "profile": fos.get("profile"),
    }
    return {
        "lecture_themes": themes,
        "basic_info": basic,
        "section_42_found": bool(themes),
        "fos_found": bool(fos.get("subject_title") or fos.get("profession")),
    }
