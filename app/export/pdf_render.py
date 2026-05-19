"""HTML → PDF (xhtml2pdf) with Cyrillic-friendly system fonts."""

from __future__ import annotations

import io
import logging
import os
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_HAS_XHTML2PDF = False
try:
    from xhtml2pdf import pisa

    _HAS_XHTML2PDF = True
except ImportError:
    pisa = None  # type: ignore


def pdf_engine_available() -> bool:
    return _HAS_XHTML2PDF


def _font_css() -> str:
    candidates = []
    if platform.system() == "Windows":
        windir = Path(os.environ.get("WINDIR", "C:/Windows"))
        candidates = [
            windir / "Fonts" / "arial.ttf",
            windir / "Fonts" / "times.ttf",
        ]
    else:
        candidates = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        ]
    for fp in candidates:
        if fp.exists():
            uri = fp.as_uri()
            return (
                f"@font-face {{ font-family: RpdPdf; src: url('{uri}'); }}\n"
                "body, p, li, h1, h2, h3 { font-family: RpdPdf, sans-serif; }\n"
            )
    return "body { font-family: sans-serif; }\n"


def html_to_pdf_bytes(html_doc: str) -> Optional[bytes]:
    if not _HAS_XHTML2PDF:
        return None
    wrapped = f"""<!doctype html>
<html><head><meta charset="utf-8"/><style>{_font_css()}</style></head>
<body>{html_doc if html_doc.lstrip().startswith('<') else f'<pre>{html_doc}</pre>'}</body></html>"""
    out = io.BytesIO()
    status = pisa.CreatePDF(wrapped, dest=out, encoding="utf-8")
    if status.err:
        logger.warning("xhtml2pdf errors: %s", status.err)
        return None
    data = out.getvalue()
    return data if data else None


def markdown_html_to_pdf_bytes(full_html: str) -> Optional[bytes]:
    """Input is full HTML document from md_to_basic_html."""
    if not _HAS_XHTML2PDF:
        return None
    if "<html" not in full_html.lower():
        return html_to_pdf_bytes(full_html)
    # Inject font CSS into head
    inject = f"<style>{_font_css()}</style>"
    if "</head>" in full_html:
        doc = full_html.replace("</head>", inject + "</head>", 1)
    else:
        doc = f"<html><head><meta charset='utf-8'/>{inject}</head><body>{full_html}</body></html>"
    out = io.BytesIO()
    status = pisa.CreatePDF(doc, dest=out, encoding="utf-8")
    if status.err:
        logger.warning("xhtml2pdf md pdf: %s", status.err)
        return None
    return out.getvalue() or None
