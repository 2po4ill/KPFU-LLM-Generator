"""
Build PPTX / resolve images from editor slides JSON (preview URLs, user uploads).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from api.presentation_preview import preview_key, resolve_preview_image
from export.slides_html import parse_slides_json
from presentation.pptx_builder import build_pptx_bytes

_SKIP_IMAGE_KINDS = frozenset({"none", "placeholder", "page_snapshot"})


def _caption_from_slide(slide: Dict[str, Any]) -> str:
    return str(slide.get("image_caption") or slide.get("image_note") or "").strip()


def assign_figure_numbers(slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Set figure_number on content slides that have a displayable image."""
    out: List[Dict[str, Any]] = []
    n = 0
    for slide in slides:
        s = dict(slide)
        layout = str(s.get("layout") or "content").lower()
        kind = str(s.get("image_kind") or "").lower()
        has_url = bool(s.get("image_url"))
        has_path = bool(s.get("image_path"))
        if (
            layout != "title"
            and kind not in _SKIP_IMAGE_KINDS
            and (has_url or has_path)
        ):
            n += 1
            s["figure_number"] = n
        else:
            s.pop("figure_number", None)
        out.append(s)
    return out


def _file_from_preview_url(image_url: str) -> Optional[str]:
    if not image_url:
        return None
    try:
        parsed = urlparse(image_url)
        qs = parse_qs(parsed.query)
        files = qs.get("file") or []
        return files[0] if files else None
    except Exception:
        return None


def _fingerprint_theme_from_url(image_url: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        qs = parse_qs(urlparse(image_url).query)
        fp = (qs.get("fingerprint") or [None])[0]
        th = (qs.get("theme_title") or [None])[0]
        return fp, th
    except Exception:
        return None, None


def resolve_slide_image_path(
    slide: Dict[str, Any],
    *,
    fingerprint: str = "",
    theme_title: str = "",
    preview_root: Optional[Path] = None,
) -> Optional[Path]:
    """Map slide image_url / image_path to a local file."""
    kind = str(slide.get("image_kind") or "").lower()
    if kind in _SKIP_IMAGE_KINDS:
        return None

    raw_path = str(slide.get("image_path") or "").strip()
    if raw_path:
        p = Path(raw_path)
        if p.is_file():
            return p

    image_url = str(slide.get("image_url") or "").strip()
    if not image_url:
        return None

    if image_url.startswith("data:"):
        return None

    fp, th = _fingerprint_theme_from_url(image_url)
    fp = fingerprint or fp or ""
    th = theme_title or th or ""
    fname = _file_from_preview_url(image_url)
    if fname and fp and th:
        path = resolve_preview_image(fp, th, fname)
        if path:
            return path

    if preview_root and fname:
        key = preview_key(fp, th) if fp and th else ""
        candidate = preview_root / key / fname if key else preview_root / fname
        if candidate.is_file():
            return candidate

    if image_url.startswith("/") or "presentation-preview/image" in image_url:
        m = re.search(r"file=([^&]+)", image_url)
        if m and fp and th:
            from urllib.parse import unquote

            return resolve_preview_image(fp, th, unquote(m.group(1)))

    if Path(image_url).is_file():
        return Path(image_url)

    return None


def slides_to_pptx_bytes(
    slides_json: str,
    *,
    theme_title: str = "",
    fingerprint: str = "",
) -> bytes:
    slides = parse_slides_json(slides_json)
    if not slides:
        return b""
    slides = assign_figure_numbers(slides)
    resolved: List[Optional[Path]] = []
    for slide in slides:
        if str(slide.get("layout") or "").lower() == "title":
            continue
        resolved.append(
            resolve_slide_image_path(
                slide,
                fingerprint=fingerprint,
                theme_title=theme_title,
            )
        )
    return build_pptx_bytes(slides, resolved, theme_title=theme_title)
