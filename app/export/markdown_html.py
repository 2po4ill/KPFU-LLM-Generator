"""Minimal Markdown → HTML for SCORM / PDF print bundles."""

from __future__ import annotations

import html
import re


def strip_html_comments(md: str) -> str:
    return re.sub(r"<!--[\s\S]*?-->", "", md or "").strip()


def md_to_basic_html(title: str, md: str) -> str:
    md = strip_html_comments(md)
    lines = (md or "").splitlines()
    out: list[str] = []
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
        "@media print{body{margin:12px}}"
        "</style>"
    )
    out.append("</head><body>")

    in_code = False
    code_buf: list[str] = []
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
            if not out or out[-1] != "<ul>":
                out.append("<ul>")
            out.append(f"<li>{html.escape(ln.strip()[2:])}</li>")
        elif not ln.strip():
            out.append("<br/>")
        else:
            if out and out[-1].startswith("<li"):
                if "<ul>" in out[-20:] and "</ul>" not in out[-20:]:
                    out.append("</ul>")
            out.append(f"<p>{html.escape(ln)}</p>")

    if out and "<ul>" in out[-40:] and "</ul>" not in out[-40:]:
        out.append("</ul>")

    out.append("</body></html>")
    return "\n".join(out)
