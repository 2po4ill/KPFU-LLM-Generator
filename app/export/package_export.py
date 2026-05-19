"""Build SCORM zip and printable HTML/PDF bundles from package artifacts."""

from __future__ import annotations

import html
import io
import zipfile
from pathlib import Path
from typing import Optional

from export.markdown_html import md_to_basic_html
from export.pdf_render import markdown_html_to_pdf_bytes, pdf_engine_available
from export.slides_html import parse_slides_json, slides_to_preview_html


def build_scorm_zip_bytes(
    *,
    course_title: str,
    lecture_md: str,
    lab_md: str = "",
    selfcheck_md: str = "",
    questions_xml: str = "",
) -> bytes:
    buf = io.BytesIO()
    lecture_html = md_to_basic_html(f"{course_title} — Лекция", lecture_md)
    lab_html = md_to_basic_html(f"{course_title} — Лабораторная", lab_md) if lab_md.strip() else ""
    selfcheck_html = (
        md_to_basic_html(f"{course_title} — Самопроверка", selfcheck_md)
        if selfcheck_md.strip()
        else ""
    )

    index_html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(course_title)}</title>
  <style>
    body{{font-family:system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px}}
    .grid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}
    a.card{{border:1px solid #e5e7eb;border-radius:12px;padding:14px;text-decoration:none;color:inherit}}
  </style>
</head>
<body>
  <h1>{html.escape(course_title)}</h1>
  <div class="grid">
    <a class="card" href="lecture.html"><strong>Лекция</strong></a>
    {"<a class='card' href='lab.html'><strong>Лабораторная</strong></a>" if lab_html else ""}
    {"<a class='card' href='selfcheck.html'><strong>Самопроверка</strong></a>" if selfcheck_html else ""}
  </div>
</body>
</html>"""

    files: dict[str, str] = {
        "index.html": index_html,
        "lecture.html": lecture_html,
    }
    if lab_html:
        files["lab.html"] = lab_html
    if selfcheck_html:
        files["selfcheck.html"] = selfcheck_html
    if questions_xml.strip():
        files["questions_moodle.xml"] = questions_xml

    file_refs = "\n".join(f'      <file href="{fn}"/>' for fn in files)
    imsmanifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="KPFU-GENERATED-COURSE" version="1.2"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
  <organizations default="ORG1">
    <organization identifier="ORG1">
      <title>{html.escape(course_title)}</title>
      <item identifier="ITEM1" identifierref="RES-INDEX">
        <title>{html.escape(course_title)}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-INDEX" type="webcontent" adlcp:scormtype="sco" href="index.html">
{file_refs}
    </resource>
  </resources>
</manifest>"""
    files["imsmanifest.xml"] = imsmanifest

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content.encode("utf-8"))
    return buf.getvalue()


def build_pdf_bundle_zip_bytes(
    *,
    course_title: str,
    lecture_md: str,
    lab_md: str = "",
    selfcheck_md: str = "",
) -> bytes:
    """ZIP of HTML pages suitable for Print → Save as PDF in browser."""
    buf = io.BytesIO()
    parts = [
        ("lecture.html", md_to_basic_html(f"{course_title} — Лекция", lecture_md)),
    ]
    if lab_md.strip():
        parts.append(("lab.html", md_to_basic_html(f"{course_title} — Лабораторная", lab_md)))
    if selfcheck_md.strip():
        parts.append(
            ("selfcheck.html", md_to_basic_html(f"{course_title} — Самопроверка", selfcheck_md))
        )

    combined_body = []
    for label, path in [("Лекция", "lecture"), ("Лабораторная", "lab"), ("Самопроверка", "selfcheck")]:
        md = {"lecture": lecture_md, "lab": lab_md, "selfcheck": selfcheck_md}[path]
        if md.strip():
            combined_body.append(f"<section><h1>{html.escape(label)}</h1>")
            inner = md_to_basic_html(label, md)
            body_start = inner.find("<body>")
            body_end = inner.find("</body>")
            if body_start >= 0 and body_end > body_start:
                combined_body.append(inner[body_start + 6 : body_end])
            combined_body.append("</section><hr/>")

    print_all = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"/>
<title>{html.escape(course_title)} — печать PDF</title>
<style>body{{font-family:system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px}}
section{{page-break-after:always}}@media print{{section{{page-break-after:always}}}}</style>
</head><body>{"".join(combined_body)}</body></html>"""

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("print_all.html", print_all.encode("utf-8"))
        zf.writestr(
            "README.txt",
            "Откройте print_all.html в браузере → Печать → Сохранить как PDF.\n".encode("utf-8"),
        )
        for name, content in parts:
            zf.writestr(name, content.encode("utf-8"))
    return buf.getvalue()


def build_native_pdf_zip_bytes(
    *,
    course_title: str,
    lecture_md: str,
    lab_md: str = "",
    selfcheck_md: str = "",
) -> tuple[bytes, bool]:
    """ZIP with .pdf files (xhtml2pdf) or HTML print bundle fallback."""
    if not pdf_engine_available():
        return (
            build_pdf_bundle_zip_bytes(
                course_title=course_title,
                lecture_md=lecture_md,
                lab_md=lab_md,
                selfcheck_md=selfcheck_md,
            ),
            False,
        )

    buf = io.BytesIO()
    entries: list[tuple[str, str, str]] = [
        ("lecture", lecture_md, "Лекция"),
    ]
    if lab_md.strip():
        entries.append(("lab", lab_md, "Лабораторная"))
    if selfcheck_md.strip():
        entries.append(("selfcheck", selfcheck_md, "Самопроверка"))

    ok_any = False
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for stem, md, label in entries:
            full_html = md_to_basic_html(f"{course_title} — {label}", md)
            pdf = markdown_html_to_pdf_bytes(full_html)
            if pdf:
                zf.writestr(f"{stem}.pdf", pdf)
                ok_any = True
            else:
                zf.writestr(f"{stem}.html", full_html.encode("utf-8"))
        if not ok_any:
            return (
                build_pdf_bundle_zip_bytes(
                    course_title=course_title,
                    lecture_md=lecture_md,
                    lab_md=lab_md,
                    selfcheck_md=selfcheck_md,
                ),
                False,
            )
    return buf.getvalue(), True


def build_presentation_pdf_bytes(
    *,
    theme_title: str,
    slides_json: str,
    fingerprint: str = "",
) -> Optional[bytes]:
    from presentation.slides_export import assign_figure_numbers, resolve_slide_image_path

    slides = assign_figure_numbers(parse_slides_json(slides_json))
    if not slides:
        return None
    for slide in slides:
        if str(slide.get("layout") or "").lower() == "title":
            continue
        path = resolve_slide_image_path(
            slide,
            fingerprint=fingerprint,
            theme_title=theme_title,
        )
        if path:
            slide["image_href"] = path.as_uri()
    html_doc = slides_to_preview_html(slides, theme_title=theme_title)
    return markdown_html_to_pdf_bytes(html_doc)
