"""
User-attached text sources for package generation (priority, bypass TOC).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional


def user_source_id(title: str, text: str) -> str:
    raw = f"{title}\n{text}".encode("utf-8")
    return "usr_" + hashlib.sha256(raw).hexdigest()[:12]


def normalize_user_sources(sources: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Validate and normalize attachment list from API/UI."""
    if not sources:
        return []
    out: List[Dict[str, Any]] = []
    max_items = 8
    max_chars = 32_000
    for raw in sources[:max_items]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip() or "Дополнительный источник"
        text = str(raw.get("text") or raw.get("content") or "").strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars]
        sid = str(raw.get("id") or "").strip() or user_source_id(title, text)
        out.append({"id": sid, "title": title, "text": text})
    return out


def user_sources_to_pages(
    sources: Optional[List[Dict[str, Any]]],
    *,
    theme: str = "",
) -> List[Dict[str, Any]]:
    """
    Convert short user texts to synthetic page dicts (skip TOC / PDF extraction).
    """
    normalized = normalize_user_sources(sources)
    pages: List[Dict[str, Any]] = []
    for idx, src in enumerate(normalized, start=1):
        header = f"# {src['title']}\n\n" if src["title"] else ""
        body = src["text"]
        if theme and theme.lower() not in body.lower()[:200]:
            header = f"{header}Тема: {theme}\n\n"
        pages.append(
            {
                "book_id": src["id"],
                "book_title": src["title"],
                "page_number": idx,
                "content": f"{header}{body}".strip(),
                "relevance_score": 1.0,
                "cached": True,
                "priority_source": True,
                "user_source": True,
                "toc_bypass": True,
            }
        )
    return pages


def split_chunks_by_priority(
    chunks: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    priority = [c for c in chunks if c.get("priority")]
    regular = [c for c in chunks if not c.get("priority")]
    return priority, regular
