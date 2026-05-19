"""
Map RPD section 4.2 lecture themes / subtopics to facet_rag section headings.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from rpd.section_parser import _norm_ws


def parse_subtopics_from_description(description: str) -> List[Dict[str, str]]:
    """Rebuild subtopics from legacy description lines (N.M title)."""
    if not description:
        return []
    out: List[Dict[str, str]] = []
    for line in description.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+\.\d+)\s+(.+)$", line)
        if m:
            out.append({"code": m.group(1), "title": _norm_ws(m.group(2)).rstrip(".")})
    return out


def normalize_theme_title(title: str) -> str:
    t = _norm_ws(title or "")
    t = re.sub(r"^тема\s+\d+\s*[\.\:]?\s*", "", t, flags=re.IGNORECASE)
    return t.lower()


def theme_order_from_title(theme_title: str) -> Optional[int]:
    m = re.search(r"тема\s+(\d+)", theme_title or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    m2 = re.match(r"^(\d+)\s*[\.\:]", (theme_title or "").strip())
    if m2:
        return int(m2.group(1))
    return None


def get_subtopics(theme_entry: Dict[str, Any]) -> List[Dict[str, str]]:
    subs = theme_entry.get("subtopics") or []
    if subs:
        return list(subs)
    return parse_subtopics_from_description(str(theme_entry.get("description") or ""))


def facet_label_from_subtopic(sub: Dict[str, str]) -> str:
    code = str(sub.get("code") or "").strip()
    title = _norm_ws(str(sub.get("title") or ""))
    if code and title:
        return f"{code}. {title}"
    return title or code


def facet_subtopic_sort_key(facet: str) -> tuple:
    """Sort key for headings like «2.1. Title» (theme.subtopic)."""
    m = re.match(r"^(\d+)\.(\d+)", (facet or "").strip())
    if m:
        return (int(m.group(1)), int(m.group(2)), (facet or "").lower())
    return (9999, 9999, (facet or "").lower())


def facets_have_rpd_codes(facets: List[str]) -> bool:
    """True when most facet headings start with N.M (RPD subtopic codes)."""
    if not facets:
        return False
    coded = sum(1 for f in facets if re.match(r"^\d+\.\d+", (f or "").strip()))
    return coded >= max(2, (len(facets) + 1) // 2)


def sort_facets_by_subtopic_code(facets: List[str]) -> List[str]:
    return sorted(facets, key=facet_subtopic_sort_key)


def facets_from_theme_entry(theme_entry: Dict[str, Any]) -> List[str]:
    """One facet heading per RPD subtopic (2.1, 2.2, …)."""
    labels: List[str] = []
    seen: set[str] = set()
    for sub in get_subtopics(theme_entry):
        label = facet_label_from_subtopic(sub)
        norm = label.lower()
        if not label or len(norm) < 4 or norm in seen:
            continue
        seen.add(norm)
        labels.append(label)
    return sort_facets_by_subtopic_code(labels)


def find_matching_lecture_theme(
    lecture_themes: List[Dict[str, Any]],
    theme_title: str,
) -> Optional[Dict[str, Any]]:
    if not lecture_themes or not theme_title:
        return None
    target_norm = normalize_theme_title(theme_title)
    target_order = theme_order_from_title(theme_title)

    for entry in lecture_themes:
        if not isinstance(entry, dict):
            continue
        if target_order is not None and int(entry.get("order") or 0) == target_order:
            return entry
        entry_norm = normalize_theme_title(str(entry.get("title") or ""))
        if entry_norm == target_norm:
            return entry
        if target_norm and (target_norm in entry_norm or entry_norm in target_norm):
            return entry
    return None


def resolve_facets_from_rpd(
    rpd_data: Optional[Dict[str, Any]],
    theme_title: str,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Returns (facet_headings, metadata).
    metadata: source=rpd|none, matched_theme, subtopics_count, ...
    """
    meta: Dict[str, Any] = {
        "source": "none",
        "matched_theme_title": None,
        "subtopics_count": 0,
    }
    if not rpd_data:
        return [], meta

    themes = rpd_data.get("lecture_themes") or []
    if not themes:
        return [], meta

    entry = find_matching_lecture_theme(themes, theme_title)
    if not entry:
        return [], meta

    facets = facets_from_theme_entry(entry)
    meta["source"] = "rpd" if facets else "none"
    meta["matched_theme_title"] = entry.get("title")
    meta["subtopics_count"] = len(get_subtopics(entry))
    meta["subtopics"] = get_subtopics(entry)
    return facets, meta
