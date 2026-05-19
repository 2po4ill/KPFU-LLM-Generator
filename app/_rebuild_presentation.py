"""Rebuild presentation.pptx (+ mermaid PNGs) from an existing smoke run folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.config import settings
from presentation.mermaid_render import render_mermaid_to_png
from presentation.pptx_builder import build_pptx_bytes
from presentation.slide_mermaid import extract_mermaid_code

BOOK_PATH = (Path(__file__).resolve().parent.parent / "uploaded_books" / "mzi.pdf").resolve()


def rebuild(run_dir: Path, theme: str = "RSA") -> int:
    slides_path = run_dir / "slides.json"
    if not slides_path.exists():
        print("slides.json not found:", slides_path)
        return 1

    slides_data = json.loads(slides_path.read_text(encoding="utf-8"))
    slides = slides_data.get("slides") or []
    assets_dir = run_dir / "presentation_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    resolved: list = []
    for slide in slides:
        if str(slide.get("layout") or "content").lower() == "title":
            continue
        img_block = slide.get("image") or {}
        mmd = extract_mermaid_code(str(img_block.get("mermaid") or ""))
        path = None
        if mmd and "A[Start]" not in mmd:
            out = assets_dir / "mermaid" / f"rebuild_{abs(hash(mmd)) % 10_000_000}.png"
            path = render_mermaid_to_png(mmd, out)
            if path:
                print("mermaid OK:", slide.get("title", "")[:50])
        if not path:
            pages = [int(p) for p in (img_block.get("source_pages") or []) if int(p) > 0]
            if pages and getattr(settings, "package_pptx_attach_page_images", True):
                from literature.pdf_figures import render_page_snapshot

                snap = assets_dir / "pages" / f"page_{pages[0]:04d}.png"
                path = render_page_snapshot(BOOK_PATH, pages[0], snap)
                if path:
                    print("page snapshot:", pages[0], slide.get("title", "")[:40])
        resolved.append(path)

    pptx_bytes = build_pptx_bytes(slides, resolved, theme_title=theme)
    out_pptx = run_dir / "presentation.pptx"
    out_pptx.write_bytes(pptx_bytes)
    print("written", out_pptx, "bytes", len(pptx_bytes))
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "../generated_package_smoke/20260517_085820_facet_rag"
    )
    raise SystemExit(rebuild(target.resolve()))
