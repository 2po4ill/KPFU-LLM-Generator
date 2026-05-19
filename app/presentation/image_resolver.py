"""
Resolve slide image requests to PDF figures or Mermaid PNG (no page snapshots, no placeholders).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature.pdf_figures import PageFigureIndex, index_pages_for_presentation, pick_figure_for_slide
from presentation.mermaid_render import render_mermaid_to_png
from presentation.slide_mermaid import extract_mermaid_code

logger = logging.getLogger(__name__)

ALGORITHM_HINTS = re.compile(
    r"(алгоритм|блок[- ]?схем|flowchart|последовательност|шаг\s*\d|схема\s+rsa|генерац)",
    re.IGNORECASE,
)


@dataclass
class ResolvedSlideImage:
    path: Optional[Path] = None
    kind: str = "none"  # figure_caption | figure_first | mermaid | user | placeholder
    note: str = ""
    caption: str = ""


@dataclass
class ImageResolver:
    page_indexes: Dict[int, PageFigureIndex] = field(default_factory=dict)
    assets_dir: Path = Path(".")

    def resolve_slide_image(self, image_block: Optional[Dict[str, Any]]) -> ResolvedSlideImage:
        if not image_block:
            return ResolvedSlideImage(kind="none")

        strategy = str(image_block.get("strategy") or "none").lower()
        image_need = str(image_block.get("image_need") or "").strip()
        figure_hint = str(image_block.get("figure_hint") or "").strip()
        caption = str(image_block.get("image_caption") or image_need or "").strip()
        source_pages = [int(p) for p in (image_block.get("source_pages") or []) if int(p) > 0]
        mermaid_src = extract_mermaid_code(str(image_block.get("mermaid") or ""))

        if strategy == "none":
            return ResolvedSlideImage(kind="none")

        if strategy == "mermaid":
            if mermaid_src:
                out = self.assets_dir / "mermaid" / f"slide_{abs(hash(mermaid_src)) % 10_000_000}.png"
                rendered = render_mermaid_to_png(mermaid_src, out)
                if rendered:
                    return ResolvedSlideImage(
                        path=rendered,
                        kind="mermaid",
                        note=caption or image_need,
                        caption=caption or image_need,
                    )
            return ResolvedSlideImage(kind="none")

        if strategy == "source":
            for page_num in source_pages:
                idx = self.page_indexes.get(page_num)
                if not idx:
                    continue
                path, kind = pick_figure_for_slide(idx, image_need, figure_hint)
                if path:
                    fig_cap = caption
                    if idx.captions and not fig_cap:
                        fig_cap = idx.captions[0].text
                    return ResolvedSlideImage(
                        path=path,
                        kind=kind,
                        note=fig_cap or f"стр. {page_num}",
                        caption=fig_cap or image_need or f"Иллюстрация, стр. {page_num}",
                    )
            return ResolvedSlideImage(kind="none")

        return ResolvedSlideImage(kind="none")


def build_image_resolver(
    pdf_path: Path,
    selected_pages: List[Dict[str, Any]],
    cache_dir: Path,
) -> ImageResolver:
    indexes = index_pages_for_presentation(pdf_path, selected_pages, cache_dir)
    return ImageResolver(page_indexes=indexes, assets_dir=cache_dir)
