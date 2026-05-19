"""
Slide geometry and text limits for PPTX export.
Used with optional template .pptx or built-in blank-slide placement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from core.config import settings


@dataclass(frozen=True)
class TextBoxSpec:
    left: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class SlideLayoutSpec:
    """All dimensions in inches (16:9, 10 × 5.625 in — matches kpfu_ru.pptx)."""
    slide_width: float = 10.0
    slide_height: float = 5.625
    title_slide_title: TextBoxSpec = TextBoxSpec(0.75, 1.75, 8.5, 1.21)
    title_slide_subtitle: TextBoxSpec = TextBoxSpec(1.5, 3.19, 7.0, 1.44)
    # TITLE_AND_BODY / Два объекта — title on top
    content_title: TextBoxSpec = TextBoxSpec(0.5, 0.23, 9.0, 0.94)
    content_body_full: TextBoxSpec = TextBoxSpec(0.5, 1.31, 9.0, 3.71)
    content_body: TextBoxSpec = TextBoxSpec(0.5, 1.31, 4.42, 3.71)
    content_image: TextBoxSpec = TextBoxSpec(5.08, 1.31, 4.42, 3.0)
    content_image_caption: TextBoxSpec = TextBoxSpec(5.08, 4.35, 4.42, 0.45)
    max_bullets: int = 5
    max_bullet_chars: int = 95
    title_max_chars: int = 72
    subtitle_max_chars: int = 120
    bullet_font_pt: int = 17
    title_font_pt: int = 32
    content_title_font_pt: int = 24


def get_layout_spec() -> SlideLayoutSpec:
    return SlideLayoutSpec(
        max_bullets=int(getattr(settings, "package_pptx_max_bullets", 5) or 5),
        max_bullet_chars=int(getattr(settings, "package_pptx_max_bullet_chars", 95) or 95),
        title_max_chars=int(getattr(settings, "package_pptx_title_max_chars", 72) or 72),
        bullet_font_pt=int(getattr(settings, "package_pptx_bullet_font_pt", 17) or 17),
        content_title_font_pt=int(
            getattr(settings, "package_pptx_content_title_font_pt", 24) or 24
        ),
    )


def resolve_template_path() -> Optional[Path]:
    raw = (getattr(settings, "package_pptx_template_path", None) or "").strip()
    if raw:
        p = Path(raw)
        return p if p.exists() else None
    templates_dir = Path(__file__).resolve().parent / "templates"
    for name in ("kpfu_ru.pptx", "simple_ru.pptx", "kpfu_default.pptx"):
        candidate = templates_dir / name
        if candidate.exists():
            return candidate
    return None


def layout_names() -> Tuple[str, str, str]:
    title = getattr(settings, "package_pptx_layout_title", "TITLE") or "TITLE"
    content = getattr(settings, "package_pptx_layout_content", "TITLE_AND_BODY") or "TITLE_AND_BODY"
    content_img = (
        getattr(settings, "package_pptx_layout_content_image", "Два объекта")
        or "Два объекта"
    )
    return title, content, content_img
