"""
Optional presentation package: lecture -> slides JSON -> PPTX with PDF figures / Mermaid.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import settings
from presentation.image_resolver import ImageResolver, ResolvedSlideImage, build_image_resolver
from presentation.mermaid_render import render_mermaid_to_png
from presentation.slide_mermaid import (
    extract_mermaid_code,
    generate_mermaid_diagram,
    sanitize_mermaid_for_cli,
)
from presentation.pptx_builder import HAS_PPTX, build_pptx_bytes
from presentation.sanitize import simplify_markdown_for_slide
from presentation.slide_planner import plan_slides_from_lecture

logger = logging.getLogger(__name__)


@dataclass
class PresentationPackageResult:
    slides_json: str = ""
    pptx_bytes: bytes = b""
    manifest: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    slides: List[Dict[str, Any]] = field(default_factory=list)
    resolved_paths: List[Optional[Path]] = field(default_factory=list)


def _apply_slide_caption(slide: Dict[str, Any], resolved: ResolvedSlideImage) -> None:
    if resolved.kind == "none" or not resolved.path:
        slide.pop("image_caption", None)
        return
    cap = (
        str(resolved.caption or "").strip()
        or str(slide.get("image_caption") or "").strip()
        or str((slide.get("image") or {}).get("image_caption") or "").strip()
        or str((slide.get("image") or {}).get("image_need") or "").strip()
        or str(slide.get("title") or "").strip()
    )
    generic = {"mermaid diagram", "mermaid", "diagram", "схема", "диаграмма", "рисунок"}
    if cap.lower() in generic:
        cap = str(slide.get("title") or "").strip()
    if cap:
        slide["image_caption"] = simplify_markdown_for_slide(cap, max_len=80)


async def _try_mermaid_for_slide(
    slide: Dict[str, Any],
    image_block: Dict[str, Any],
    assets_dir: Path,
    llm_generate,
) -> ResolvedSlideImage:
    raw_mmd = str(image_block.get("mermaid") or "").strip()
    mmd = extract_mermaid_code(raw_mmd) if raw_mmd else ""
    if not mmd:
        mmd = await generate_mermaid_diagram(
            str(image_block.get("image_need") or slide.get("title") or ""),
            [str(b) for b in (slide.get("bullets") or [])],
            llm_generate,
        )
        image_block["mermaid"] = sanitize_mermaid_for_cli(mmd)
    out = assets_dir / "mermaid" / f"slide_{abs(hash(mmd)) % 10_000_000}.png"
    rendered = render_mermaid_to_png(mmd, out)
    caption = str(
        image_block.get("image_caption")
        or image_block.get("image_need")
        or slide.get("title")
        or ""
    ).strip()
    if rendered:
        return ResolvedSlideImage(
            path=rendered,
            kind="mermaid",
            note=caption,
            caption=caption,
        )
    return ResolvedSlideImage(kind="none")


async def build_presentation_from_lecture(
    *,
    theme: str,
    lecture_md: str,
    selected_pages: List[Dict[str, Any]],
    pdf_path: Path,
    rpd_data: Dict[str, Any],
    llm_generate,
    assets_dir: Path,
    concept_cards: Optional[List[Any]] = None,
) -> PresentationPackageResult:
    warnings: List[str] = []
    if not HAS_PPTX:
        return PresentationPackageResult(
            warnings=["python-pptx not installed; PPTX skipped"],
        )

    subject = str(rpd_data.get("subject_title") or "")
    max_slides = int(getattr(settings, "package_pptx_max_slides", 18) or 18)
    max_bullets = int(getattr(settings, "package_pptx_max_bullets", 4) or 4)
    max_bullet_chars = int(getattr(settings, "package_pptx_max_bullet_chars", 140) or 140)

    slides_data = await plan_slides_from_lecture(
        theme=theme,
        lecture_md=lecture_md,
        subject_title=subject,
        llm_generate=llm_generate,
        max_slides=max_slides,
        max_bullets=max_bullets,
        max_bullet_chars=max_bullet_chars,
    )
    slides: List[Dict[str, Any]] = list(slides_data.get("slides") or [])

    resolver: Optional[ImageResolver] = None
    try:
        resolver = build_image_resolver(pdf_path, selected_pages, assets_dir)
    except Exception as e:
        warnings.append(f"figure index: {e}")

    resolved_paths: List[Optional[Path]] = []
    manifest_slides: List[Dict[str, Any]] = []

    for slide in slides:
        if str(slide.get("layout") or "").lower() == "title":
            continue

        image_block = slide.get("image") if isinstance(slide.get("image"), dict) else {}
        strategy = str((image_block or {}).get("strategy") or "none").lower()

        resolved = ResolvedSlideImage(kind="none")
        if strategy == "mermaid":
            try:
                resolved = await _try_mermaid_for_slide(
                    slide, image_block, assets_dir, llm_generate
                )
            except Exception as e:
                warnings.append(f"mermaid: {e}")
        elif strategy == "source" and resolver:
            resolved = resolver.resolve_slide_image(image_block)

        path = resolved.path if resolved.kind != "none" and resolved.path else None
        _apply_slide_caption(slide, resolved)

        resolved_paths.append(path)
        manifest_slides.append(
            {
                "title": slide.get("title"),
                "image_kind": resolved.kind if path else "none",
                "image_path": str(path) if path else None,
                "image_note": resolved.caption or resolved.note,
                "image_caption": slide.get("image_caption"),
                "source_pages": (image_block or {}).get("source_pages"),
            }
        )

    try:
        pptx_bytes = build_pptx_bytes(slides, resolved_paths, theme_title=theme)
    except Exception as e:
        warnings.append(f"pptx build: {e}")
        pptx_bytes = b""

    manifest = {
        "theme": theme,
        "pdf_path": str(pdf_path),
        "slide_count": len([s for s in slides if str(s.get("layout") or "").lower() != "title"]),
        "slides": manifest_slides,
    }
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "slides.json").write_text(
        json.dumps(slides_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (assets_dir / "presentation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return PresentationPackageResult(
        slides_json=json.dumps(slides_data, ensure_ascii=False, indent=2),
        pptx_bytes=pptx_bytes,
        manifest=manifest,
        warnings=warnings,
        slides=slides,
        resolved_paths=resolved_paths,
    )
