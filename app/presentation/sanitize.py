"""
Strip HTML / provenance / heavy markdown from text shown in PPTX or reader-facing lecture.
"""

from __future__ import annotations

import re

_HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CONCEPT_ORIGIN_RE = re.compile(
    r'<!--\s*CONCEPT_ORIGIN:\s*concept="[^"]*";\s*pages=\[([^\]]*)\]',
    re.IGNORECASE,
)


def parse_concept_origin_pages(text: str) -> list[int]:
    m = _CONCEPT_ORIGIN_RE.search(text or "")
    if not m:
        return []
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def strip_html_and_comments(text: str) -> str:
    s = _HTML_COMMENT_RE.sub("", text or "")
    s = _HTML_TAG_RE.sub("", s)
    return s.strip()


def simplify_markdown_for_slide(text: str, *, max_len: int = 160) -> str:
    s = strip_html_and_comments(text)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # LaTeX inline/display (keep words, drop delimiters)
    s = re.sub(r"\\\(|\\\)|\\\[|\\\]", "", s)
    s = re.sub(r"\\mathbb\{([^}]+)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def is_noise_bullet(text: str) -> bool:
    s = (text or "").strip()
    if not s or s.startswith("<!--") or "CONCEPT_ORIGIN" in s:
        return True
    if s.startswith("Глава ") and len(s) > 80:
        return True
    if s.count("claims=") > 0 and len(s) > 60:
        return True
    return False
