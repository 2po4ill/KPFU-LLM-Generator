import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--[\s\S]*?-->", "", text or "").strip()


def md_to_basic_html(title: str, md: str) -> str:
    md = strip_html_comments(md)
    lines = (md or "").splitlines()
    out: List[str] = []
    out.append("<!doctype html>")
    out.append('<html lang="ru">')
    out.append("<head>")
    out.append('<meta charset="utf-8"/>')
    out.append('<meta name="viewport" content="width=device-width, initial-scale=1"/>')
    out.append(f"<title>{html.escape(title)}</title>")
    out.append(
        "<style>"
        "body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:1020px;margin:24px auto;padding:0 16px;line-height:1.5}"
        "pre,code{font-family:ui-monospace,Consolas,monospace}"
        "pre{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}"
        "h1,h2,h3{margin-top:1.2em}"
        "hr{margin:20px 0}"
        "a{color:#0b57d0;text-decoration:none}"
        "a:hover{text-decoration:underline}"
        ".muted{color:#666}"
        "</style>"
    )
    out.append("</head><body>")

    in_code = False
    code_buf: List[str] = []
    in_ul = False

    def _close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for ln in lines:
        if ln.strip().startswith("```"):
            if not in_code:
                _close_ul()
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
            _close_ul()
            out.append(f"<h1>{html.escape(ln[2:].strip())}</h1>")
        elif ln.startswith("## "):
            _close_ul()
            out.append(f"<h2>{html.escape(ln[3:].strip())}</h2>")
        elif ln.startswith("### "):
            _close_ul()
            out.append(f"<h3>{html.escape(ln[4:].strip())}</h3>")
        elif ln.strip() == "---":
            _close_ul()
            out.append("<hr/>")
        elif ln.strip().startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(ln.strip()[2:])}</li>")
        elif not ln.strip():
            _close_ul()
            out.append("<br/>")
        else:
            _close_ul()
            out.append(f"<p>{html.escape(ln)}</p>")

    _close_ul()
    out.append("</body></html>")
    return "\n".join(out)


@dataclass
class ThemePackage:
    slug: str
    title: str
    lecture_md: str
    lab_md: str
    selfcheck_md: str
    questions_xml: str


def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9а-яё]+", "-", s, flags=re.I)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "theme"


def _infer_title_from_md(md: str, fallback: str) -> str:
    md = md or ""
    for pat in [r"^#\s+Самопроверка:\s*(.+)$", r"^#\s+Лабораторная работа:\s*(.+)$", r"^#\s+(.+)$"]:
        m = re.search(pat, md, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    return fallback


def load_theme_packages(root: Path) -> List[ThemePackage]:
    """
    Expected structure:
      <root>/
        01-<slug>/lecture.md
        01-<slug>/lab.md
        01-<slug>/selfcheck.md
        01-<slug>/questions_moodle.xml (optional)

    Also supports: generated_package_smoke/{lecture_smoke.md,lab_smoke.md,selfcheck_smoke.md,questions_moodle.xml}
    """
    pkgs: List[ThemePackage] = []

    # Special-case: smoke folder
    if (root / "lecture_smoke.md").exists() and (root / "selfcheck_smoke.md").exists():
        lecture_md = (root / "lecture_smoke.md").read_text(encoding="utf-8")
        lab_md = (root / "lab_smoke.md").read_text(encoding="utf-8") if (root / "lab_smoke.md").exists() else ""
        selfcheck_md = (root / "selfcheck_smoke.md").read_text(encoding="utf-8")
        qxml = (root / "questions_moodle.xml").read_text(encoding="utf-8") if (root / "questions_moodle.xml").exists() else ""
        title = _infer_title_from_md(selfcheck_md, "Theme")
        pkgs.append(
            ThemePackage(
                slug=_slugify(title),
                title=title,
                lecture_md=lecture_md,
                lab_md=lab_md,
                selfcheck_md=selfcheck_md,
                questions_xml=qxml,
            )
        )
        return pkgs

    for d in sorted([p for p in root.iterdir() if p.is_dir()]):
        lecture_p = d / "lecture.md"
        lab_p = d / "lab.md"
        self_p = d / "selfcheck.md"
        if not (lecture_p.exists() and lab_p.exists() and self_p.exists()):
            continue
        lecture_md = lecture_p.read_text(encoding="utf-8")
        lab_md = lab_p.read_text(encoding="utf-8")
        selfcheck_md = self_p.read_text(encoding="utf-8")
        qxml_p = d / "questions_moodle.xml"
        qxml = qxml_p.read_text(encoding="utf-8") if qxml_p.exists() else ""
        title = _infer_title_from_md(selfcheck_md, d.name)
        pkgs.append(
            ThemePackage(
                slug=_slugify(d.name),
                title=title,
                lecture_md=lecture_md,
                lab_md=lab_md,
                selfcheck_md=selfcheck_md,
                questions_xml=qxml,
            )
        )
    return pkgs


def build_scorm_course_zip(
    *,
    course_title: str,
    theme_packages: List[ThemePackage],
    out_zip: Path,
) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()

    # Render files in-memory then zip them.
    files: List[tuple[str, str]] = []

    # Course index
    items_html = []
    for idx, t in enumerate(theme_packages, start=1):
        base = f"themes/{idx:02d}-{t.slug}"
        items_html.append(
            f'<li><strong>{html.escape(t.title)}</strong>: '
            f'<a href="{base}/lecture.html">лекция</a> · '
            f'<a href="{base}/lab.html">лаба</a> · '
            f'<a href="{base}/selfcheck.html">самопроверка</a>'
            f'</li>'
        )
    index = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(course_title)}</title>
  <style>
    body{{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:1020px;margin:24px auto;padding:0 16px;line-height:1.5}}
    .muted{{color:#666}}
    code{{font-family:ui-monospace,Consolas,monospace}}
    a{{color:#0b57d0;text-decoration:none}}
    a:hover{{text-decoration:underline}}
  </style>
</head>
<body>
  <h1>{html.escape(course_title)}</h1>
  <p class="muted">SCORM‑курс предпросмотра. Для Moodle Quiz: импортируй XML вопросов в банк вопросов.</p>
  <h2>Темы</h2>
  <ol>
    {''.join(items_html)}
  </ol>
  <hr/>
  <h2>Импорт вопросов</h2>
  <p class="muted">Файлы <code>questions_moodle.xml</code> лежат в папках тем внутри SCORM‑архива.</p>
</body>
</html>
"""
    files.append(("index.html", index))

    # Theme pages + xml
    for idx, t in enumerate(theme_packages, start=1):
        base = f"themes/{idx:02d}-{t.slug}"
        files.append((f"{base}/lecture.html", md_to_basic_html(f"{t.title} — Лекция", t.lecture_md)))
        files.append((f"{base}/lab.html", md_to_basic_html(f"{t.title} — Лабораторная", t.lab_md)))
        files.append((f"{base}/selfcheck.html", md_to_basic_html(f"{t.title} — Самопроверка", t.selfcheck_md)))
        files.append((f"{base}/questions_moodle.xml", t.questions_xml or ""))

    # SCORM manifest (single SCO launching index.html)
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
      {''.join([f'<file href=\"{html.escape(path)}\"/>' for path, _ in files if path != 'index.html'])}
    </resource>
  </resources>
</manifest>
"""
    files.append(("imsmanifest.xml", imsmanifest))

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in files:
            zf.writestr(path, content)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    # Default input: generated_course_packages/ OR fallback to generated_package_smoke/
    default_in = root / "generated_course_packages"
    if default_in.exists():
        in_dir = default_in
    else:
        in_dir = root / "generated_package_smoke"

    pkgs = load_theme_packages(in_dir)
    if not pkgs:
        raise SystemExit(f"No theme packages found in: {in_dir}")

    out_zip = root / "generated_moodle_package" / "scorm_course.zip"
    build_scorm_course_zip(course_title="SCORM course preview", theme_packages=pkgs, out_zip=out_zip)
    print(f"Built: {out_zip}")
    print(f"Themes: {len(pkgs)} (from {in_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

