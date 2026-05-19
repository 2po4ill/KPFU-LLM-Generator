"""
Extract embedded images and figure captions from PDF pages (PyMuPDF).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

CAPTION_PATTERNS = [
    re.compile(
        r"(?:Рис(?:унок)?\.?|Рис\.)\s*(\d+(?:\.\d+)*)\s*[\.—\-–:]?\s*(.{10,200}?)(?=\n|Рис\.|Рисунок|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:Fig(?:ure)?\.?)\s*(\d+(?:\.\d+)*)\s*[\.—\-–:]?\s*(.{10,200}?)(?=\n|Fig\.|$)",
        re.IGNORECASE | re.DOTALL,
    ),
]


@dataclass
class FigureCaption:
    number: str
    text: str
    page_number: int


@dataclass
class ExtractedFigure:
    page_number: int
    index_on_page: int
    path: Path
    width: int = 0
    height: int = 0
    caption: Optional[FigureCaption] = None


@dataclass
class PageFigureIndex:
    page_number: int
    figures: List[ExtractedFigure] = field(default_factory=list)
    captions: List[FigureCaption] = field(default_factory=list)
    page_snapshot_path: Optional[Path] = None


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-яё0-9]+", (text or "").lower()))


def caption_match_score(caption_text: str, image_need: str, figure_hint: str = "") -> float:
    a = _token_set(caption_text) | _token_set(figure_hint)
    b = _token_set(image_need)
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


def parse_figure_captions(page_text: str, page_number: int) -> List[FigureCaption]:
    text = (page_text or "").replace("\r", "\n")
    found: List[FigureCaption] = []
    seen: set[str] = set()
    for pattern in CAPTION_PATTERNS:
        for m in pattern.finditer(text):
            num = m.group(1).strip()
            body = re.sub(r"\s+", " ", (m.group(2) or "").strip())
            key = f"{num}:{body[:40]}"
            if key in seen or len(body) < 5:
                continue
            seen.add(key)
            found.append(FigureCaption(number=num, text=body, page_number=page_number))
    return found


def render_page_snapshot(
    pdf_path: Path,
    page_number: int,
    out_path: Path,
    *,
    dpi: int = 150,
) -> Optional[Path]:
    if not HAS_PYMUPDF:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pix.save(str(out_path))
        doc.close()
        return out_path
    except Exception as e:
        logger.warning("page snapshot failed p%s: %s", page_number, e)
        return None


def extract_page_figures(
    pdf_path: Path,
    page_number: int,
    out_dir: Path,
    *,
    min_bytes: int = 800,
) -> List[ExtractedFigure]:
    if not HAS_PYMUPDF:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    figures: List[ExtractedFigure] = []
    try:
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return []
        page = doc[page_number - 1]
        rects: List[Any] = []
        try:
            rects = page.get_image_rects()  # type: ignore[attr-defined]
        except Exception:
            rects = []

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                base = doc.extract_image(xref)
            except Exception:
                continue
            data = base.get("image") or b""
            if len(data) < min_bytes:
                continue
            ext = base.get("ext") or "png"
            if ext == "jpeg":
                ext = "jpg"
            path = out_dir / f"p{page_number:04d}_fig{img_index:02d}.{ext}"
            path.write_bytes(data)
            w = int(base.get("width") or 0)
            h = int(base.get("height") or 0)
            figures.append(
                ExtractedFigure(
                    page_number=page_number,
                    index_on_page=img_index,
                    path=path,
                    width=w,
                    height=h,
                )
            )

        # Prefer larger diagrams when multiple assets exist.
        figures.sort(key=lambda f: (f.width * f.height, f.path.stat().st_size), reverse=True)
        doc.close()
        return figures
    except Exception as e:
        logger.warning("extract_page_figures failed p%s: %s", page_number, e)
        return []


def build_page_figure_index(
    pdf_path: Path,
    page_number: int,
    page_text: str,
    cache_dir: Path,
) -> PageFigureIndex:
    page_dir = cache_dir / f"page_{page_number:04d}"
    captions = parse_figure_captions(page_text, page_number)
    figures = extract_page_figures(pdf_path, page_number, page_dir / "figures")
    for fig in figures:
        best_cap: Optional[FigureCaption] = None
        best_score = 0.0
        for cap in captions:
            sc = caption_match_score(cap.text, cap.text, cap.number)
            if sc > best_score:
                best_score = sc
                best_cap = cap
        fig.caption = best_cap

    return PageFigureIndex(
        page_number=page_number,
        figures=figures,
        captions=captions,
        page_snapshot_path=None,
    )


def pick_figure_for_slide(
    index: PageFigureIndex,
    image_need: str,
    figure_hint: str = "",
) -> Tuple[Optional[Path], str]:
    """
    Returns (image_path, resolution_kind).
    resolution_kind: figure_caption | figure_first | none
    """
    if not image_need and not figure_hint:
        return None, "none"

    if index.captions and index.figures:
        best_fig: Optional[ExtractedFigure] = None
        best_score = 0.0
        for fig in index.figures:
            cap_text = fig.caption.text if fig.caption else ""
            hint = figure_hint or (fig.caption.number if fig.caption else "")
            sc = caption_match_score(cap_text, image_need, hint)
            if figure_hint and fig.caption and fig.caption.number in figure_hint:
                sc = max(sc, 0.75)
            if sc > best_score:
                best_score = sc
                best_fig = fig
        if best_fig and best_score >= 0.12:
            return best_fig.path, "figure_caption"

    if index.figures:
        return index.figures[0].path, "figure_first"

    return None, "none"


def index_pages_for_presentation(
    pdf_path: Path,
    pages: List[Dict[str, Any]],
    cache_dir: Path,
) -> Dict[int, PageFigureIndex]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out: Dict[int, PageFigureIndex] = {}
    for p in pages:
        page_num = int(p.get("page_number") or 0)
        if page_num <= 0:
            continue
        text = str(p.get("content") or "")
        out[page_num] = build_page_figure_index(pdf_path, page_num, text, cache_dir)
    return out
