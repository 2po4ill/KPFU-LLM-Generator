"""
Visible provenance markers in markdown for expert review (human-in-the-loop).
"""

from __future__ import annotations

import json
import re
from typing import List


_ORIGIN_RE = re.compile(
    r"<!--\s*CONCEPT_ORIGIN:\s*concept=\"([^\"]*)\";\s*pages=\[([^\]]*)\];\s*book=\"([^\"]*)\";\s*claims=(.*?)\s*-->",
    re.DOTALL,
)


def provenance_comment_to_blockquote(comment_line: str) -> str:
    m = _ORIGIN_RE.search(comment_line)
    if not m:
        return comment_line
    concept, pages_raw, book, claims_raw = m.groups()
    pages = pages_raw.strip()
    book = book.strip() or "—"
    try:
        claims = json.loads(claims_raw)
        n_claims = len(claims) if isinstance(claims, list) else 0
    except json.JSONDecodeError:
        n_claims = 0
    book_line = _format_book_markdown(book)
    return (
        f"> **Источник** · тема «{concept}» · стр. {pages or '—'} · {book_line}"
        f" · утверждений в базе: {n_claims}\n"
        f"> `CONCEPT_ORIGIN` — не удаляйте блок при правке, если нужен экспорт в Moodle/SCORM.\n"
    )


def _format_book_markdown(book: str) -> str:
    """Render book field as title and optional markdown link (title | url)."""
    raw = (book or "").strip()
    if not raw:
        return "—"
    if " | http" in raw:
        title, url = raw.split(" | ", 1)
        title = title.strip() or url.strip()
        url = url.strip()
        return f"[{title}]({url})"
    if raw.startswith("http://") or raw.startswith("https://"):
        return f"[источник]({raw})"
    return raw


def lecture_with_visible_provenance(markdown: str) -> str:
    """Turn HTML CONCEPT_ORIGIN comments into visible blockquote markers."""
    out: List[str] = []
    for line in (markdown or "").splitlines():
        if "CONCEPT_ORIGIN:" in line and line.strip().startswith("<!--"):
            out.append(provenance_comment_to_blockquote(line))
        else:
            out.append(line)
    return "\n".join(out).strip()


def strip_visible_provenance_for_students(markdown: str) -> str:
    """Remove visible source blockquotes and HTML comments for student-facing text."""
    lines = []
    skip_blockquote = False
    for line in (markdown or "").splitlines():
        if line.strip().startswith("<!--"):
            continue
        if line.strip().startswith("> **Источник**"):
            skip_blockquote = True
            continue
        if skip_blockquote and line.strip().startswith(">"):
            continue
        skip_blockquote = False
        lines.append(line)
    return "\n".join(lines).strip()
