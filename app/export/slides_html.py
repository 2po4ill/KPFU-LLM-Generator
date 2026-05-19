"""Render slides.json to HTML for preview / PDF export."""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List

from presentation.pptx_builder import format_figure_caption


def parse_slides_json(raw: str) -> List[Dict[str, Any]]:
    if not (raw or "").strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    return list(data.get("slides") or [])


def slides_to_preview_html(slides: List[Dict[str, Any]], *, theme_title: str = "") -> str:
    parts = [
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'/>",
        "<title>",
        html.escape(theme_title or "Презентация"),
        "</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f1f5f9}",
        ".deck{display:flex;flex-direction:column;gap:16px;max-width:920px;margin:0 auto}",
        ".slide{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;box-shadow:0 4px 12px rgba(0,0,0,.06)}",
        ".slide--title{text-align:center;padding:48px 24px}",
        ".slide__row{display:flex;gap:20px;align-items:flex-start}",
        ".slide__text{flex:1;min-width:0}",
        ".slide__media{flex:0 0 42%;max-width:380px}",
        ".slide__media img{max-width:100%;height:auto;border-radius:8px;border:1px solid #e2e8f0}",
        ".slide__figcap{margin-top:6px;font-size:0.85rem;color:#475569;text-align:center}",
        ".slide h2{margin:0 0 12px;font-size:1.25rem}",
        ".slide--title h2{font-size:1.6rem}",
        ".muted{color:#64748b}",
        "ul{margin:8px 0 0;padding-left:1.2rem}",
        "li{margin:4px 0}",
        "@media print{.slide{page-break-after:always;box-shadow:none}}",
        "</style></head><body>",
        "<div class='deck'>",
    ]
    for s in slides:
        layout = str(s.get("layout") or "content").lower()
        title = html.escape(str(s.get("title") or ""))
        subtitle = html.escape(str(s.get("subtitle") or ""))
        cls = "slide slide--title" if layout == "title" else "slide"
        parts.append(f"<section class='{cls}'>")
        if layout == "title":
            parts.append(f"<h2>{title}</h2>")
            if subtitle:
                parts.append(f"<p class='muted'>{subtitle}</p>")
            parts.append("</section>")
            continue
        parts.append("<div class='slide__row'>")
        parts.append("<motion.div class='slide__text'>")
        parts[-1] = "<div class='slide__text'>"
        parts.append(f"<h2>{title}</h2>")
        bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()]
        if bullets:
            parts.append("<ul>")
            for b in bullets[:8]:
                parts.append(f"<li>{html.escape(b[:200])}</li>")
            parts.append("</ul>")
        parts.append("</div>")
        img_href = str(s.get("image_href") or "").strip()
        cap = format_figure_caption(s)
        if img_href:
            parts.append("<div class='slide__media'>")
            parts.append(
                f"<img src='{html.escape(img_href, quote=True)}' alt=''/>"
            )
            if cap:
                parts.append(f"<p class='slide__figcap'>{html.escape(cap)}</p>")
            parts.append("</div>")
        parts.append("</div></section>")
    parts.append("</div></body></html>")
    return "".join(parts)
