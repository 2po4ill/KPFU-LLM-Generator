import html
import os
import re
import zipfile
from pathlib import Path


def strip_html_comments(md: str) -> str:
    # Remove provenance markers from student-facing HTML view.
    return re.sub(r"<!--[\s\S]*?-->", "", md or "").strip()


def md_to_basic_html(title: str, md: str) -> str:
    """
    Minimal, dependency-free Markdown -> HTML renderer.
    Goal: readable preview in Moodle/SCORM, not perfect markdown fidelity.
    """
    md = strip_html_comments(md)
    lines = (md or "").splitlines()
    out = []
    out.append("<!doctype html>")
    out.append('<html lang="ru">')
    out.append("<head>")
    out.append('<meta charset="utf-8"/>')
    out.append('<meta name="viewport" content="width=device-width, initial-scale=1"/>')
    out.append(f"<title>{html.escape(title)}</title>")
    out.append(
        "<style>"
        "body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;line-height:1.45}"
        "pre,code{font-family:ui-monospace,Consolas,monospace}"
        "pre{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}"
        "h1,h2,h3{margin-top:1.2em}"
        "hr{margin:20px 0}"
        "a{color:#0b57d0;text-decoration:none}"
        "a:hover{text-decoration:underline}"
        "</style>"
    )
    out.append("</head><body>")

    in_code = False
    code_buf = []
    for ln in lines:
        if ln.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                out.append("<pre><code>")
                out.append(html.escape("\n".join(code_buf)))
                out.append("</code></pre>")
            continue
        if in_code:
            code_buf.append(ln)
            continue

        if ln.startswith("# "):
            out.append(f"<h1>{html.escape(ln[2:].strip())}</h1>")
        elif ln.startswith("## "):
            out.append(f"<h2>{html.escape(ln[3:].strip())}</h2>")
        elif ln.startswith("### "):
            out.append(f"<h3>{html.escape(ln[4:].strip())}</h3>")
        elif ln.strip() == "---":
            out.append("<hr/>")
        elif ln.strip().startswith("- "):
            # very simple list handling: wrap each item in <li>; open/close per block
            # We'll just emit <ul> around each list-run.
            # Look back to see if previous element is <ul>.
            if not out or out[-1] != "<ul>":
                out.append("<ul>")
            out.append(f"<li>{html.escape(ln.strip()[2:])}</li>")
        elif not ln.strip():
            # close list if open
            if out and out[-1].startswith("<li") and "<ul>" in out[-2:]:
                # ensure we close only once per run
                # walk back: if we have an open <ul> without close, close it.
                pass
            out.append("<br/>")
        else:
            # close list if we were in one
            if out and out[-1].startswith("<li"):
                # find last <ul> marker without close; easiest: close if last emitted was li and some ul exists near end
                # ensure we don't spam closes by checking last close
                if "<ul>" in out[-20:] and "</ul>" not in out[-20:]:
                    out.append("</ul>")
            out.append(f"<p>{html.escape(ln)}</p>")

    # close any open list at end
    if out and "<ul>" in out[-40:] and "</ul>" not in out[-40:]:
        out.append("</ul>")

    out.append("</body></html>")
    return "\n".join(out)


def build_scorm_zip(
    *,
    source_dir: Path,
    out_zip: Path,
    course_title: str,
    lecture_md: str,
    lab_md: str,
    selfcheck_md: str,
    questions_xml: str,
) -> None:
    work = Path(".scorm_build_tmp")
    if work.exists():
        for p in work.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted([p for p in work.rglob("*") if p.is_dir()], reverse=True):
            try:
                p.rmdir()
            except OSError:
                pass
        try:
            work.rmdir()
        except OSError:
            pass
    work.mkdir(parents=True, exist_ok=True)

    (work / "lecture.html").write_text(
        md_to_basic_html(f"{course_title} — Лекция", lecture_md), encoding="utf-8"
    )
    (work / "lab.html").write_text(
        md_to_basic_html(f"{course_title} — Лабораторная", lab_md), encoding="utf-8"
    )
    (work / "selfcheck.html").write_text(
        md_to_basic_html(f"{course_title} — Самопроверка", selfcheck_md),
        encoding="utf-8",
    )
    (work / "questions_moodle.xml").write_text(questions_xml or "", encoding="utf-8")

    index_html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(course_title)}</title>
  <style>
    body{{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;line-height:1.45}}
    .grid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin-top:16px}}
    a.card{{border:1px solid #e5e7eb;border-radius:12px;padding:14px;text-decoration:none;color:inherit}}
    a.card:hover{{border-color:#0b57d0}}
    .muted{{color:#666}}
    code{{font-family:ui-monospace,Consolas,monospace}}
  </style>
</head>
<body>
  <h1>{html.escape(course_title)}</h1>
  <p class="muted">SCORM-пакет предпросмотра.</p>
  <div class="grid">
    <a class="card" href="lecture.html"><strong>Лекция</strong><br/><span class="muted">lecture.html</span></a>
    <a class="card" href="lab.html"><strong>Лабораторная</strong><br/><span class="muted">lab.html</span></a>
    <a class="card" href="selfcheck.html"><strong>Самопроверка</strong><br/><span class="muted">selfcheck.html</span></a>
  </div>
</body>
</html>
"""
    (work / "index.html").write_text(index_html, encoding="utf-8")

    # Minimal SCORM 1.2 manifest: 3 resources + launch index.html
    imsmanifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="KPFU-GENERATED-COURSE" version="1.2"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="
    http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
    http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
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
      <file href="index.html"/>
      <file href="lecture.html"/>
      <file href="lab.html"/>
      <file href="selfcheck.html"/>
      <file href="questions_moodle.xml"/>
    </resource>
  </resources>
</manifest>
"""
    (work / "imsmanifest.xml").write_text(imsmanifest, encoding="utf-8")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in ["imsmanifest.xml", "index.html", "lecture.html", "lab.html", "selfcheck.html", "questions_moodle.xml"]:
            zf.write(work / fp, arcname=fp)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "generated_package_smoke"
    lecture = (src / "lecture_smoke.md").read_text(encoding="utf-8")
    lab = (src / "lab_smoke.md").read_text(encoding="utf-8")
    selfcheck = (src / "selfcheck_smoke.md").read_text(encoding="utf-8")
    qxml_path = src / "questions_moodle.xml"
    qxml = qxml_path.read_text(encoding="utf-8") if qxml_path.exists() else ""
    course_title = "Generated course preview"
    # Try infer theme from self-check header
    m = re.search(r"^#\s+Самопроверка:\s*(.+)$", selfcheck, flags=re.MULTILINE)
    if m:
        course_title = m.group(1).strip()
    out_zip = root / "generated_moodle_package" / "course_scorm_preview.zip"
    build_scorm_zip(
        source_dir=src,
        out_zip=out_zip,
        course_title=course_title,
        lecture_md=lecture,
        lab_md=lab,
        selfcheck_md=selfcheck,
        questions_xml=qxml,
    )
    print(f"Built: {out_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

