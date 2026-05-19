"""
Discover and normalize source URLs from RPD raw text (regex; no LLM).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Set
from urllib.parse import urldefrag, urlparse, urlunparse

_URL_RE = re.compile(
    r"(?P<url>https?://[^\s\]\)\"\'<>,]+|www\.[^\s\]\)\"\'<>,]+)",
    re.IGNORECASE,
)


def _strip_trailing_junk(url: str) -> str:
    u = url.rstrip(".,;:)\"'»")
    while u.endswith(")"):
        u = u[:-1].rstrip(".,;:\"'»")
    return u


def normalize_url(url: str) -> str:
    u = url.strip()
    if u.lower().startswith("www."):
        u = "https://" + u
    u = _strip_trailing_junk(u)
    u, _frag = urldefrag(u)
    parsed = urlparse(u)
    if not parsed.scheme or not parsed.netloc:
        return u
    netloc = parsed.netloc.lower()
    path = parsed.path or ""
    if netloc.endswith(":80") and parsed.scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and parsed.scheme == "https":
        netloc = netloc[:-4]
    clean = urlunparse(
        (parsed.scheme.lower(), netloc, path, "", parsed.query, "")
    )
    return clean.rstrip("/") or u


def classify_url(url: str) -> str:
    p = urlparse(url)
    path = (p.path or "").lower()
    if path.endswith(".pdf"):
        return "direct_pdf"
    if "pdf" in path.split("/")[-1] or "/pdf" in path:
        return "direct_pdf"
    if p.scheme in ("http", "https") and p.netloc:
        return "http_page"
    return "unknown"


def _iter_urls(raw_text: str) -> List[str]:
    if not raw_text:
        return []
    found: List[str] = []
    for m in _URL_RE.finditer(raw_text):
        u = normalize_url(m.group("url"))
        if u.startswith("http"):
            found.append(u)
    return found


def build_normalized_sources(
    raw_text: str,
    literature_references: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    literature_references = literature_references or []
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []

    def add(url: str, title_hint: str | None = None) -> None:
        nu = normalize_url(url)
        if nu in seen:
            return
        seen.add(nu)
        sid = hashlib.sha256(nu.encode("utf-8")).hexdigest()[:16]
        kind = classify_url(nu)
        out.append(
            {
                "id": sid,
                "url": url if url.startswith("http") else nu,
                "normalized_url": nu,
                "kind": kind,
                "title_hint": title_hint,
                "status": "pending",
                "sha256": None,
                "storage_relpath": None,
                "book_id": None,
                "error": None,
            }
        )

    for ref in literature_references:
        u = ref.get("url")
        if isinstance(u, str) and u.strip():
            hint = ref.get("title") or ref.get("authors")
            add(u.strip(), str(hint) if hint else None)

    for u in _iter_urls(raw_text):
        add(u, None)

    return out
