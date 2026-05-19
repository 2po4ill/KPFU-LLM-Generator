"""
Generate starter kpfu_default.pptx for manual polish in PowerPoint.

Run from app/:
  python -m presentation.generate_template

Creates layouts by duplicating a base presentation — edit names in PowerPoint:
  - KPFU Title
  - KPFU Content
  - KPFU Content Image
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

from presentation.layout_spec import get_layout_spec


def main() -> None:
    limits = get_layout_spec()
    out = Path(__file__).resolve().parent / "templates" / "kpfu_default.pptx"
    out.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(limits.slide_width)
    prs.slide_height = Inches(limits.slide_height)
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]

    # Title reference slide
    s0 = prs.slides.add_slide(blank)
    box = s0.shapes.add_textbox(
        Inches(limits.title_slide_title.left),
        Inches(limits.title_slide_title.top),
        Inches(limits.title_slide_title.width),
        Inches(limits.title_slide_title.height),
    )
    box.text_frame.text = "Тема лекции"
    box.text_frame.paragraphs[0].font.size = Pt(limits.title_font_pt)

    # Content reference
    s1 = prs.slides.add_slide(blank)
    s1.shapes.add_textbox(
        Inches(limits.content_title.left),
        Inches(limits.content_title.top),
        Inches(limits.content_title.width),
        Inches(limits.content_title.height),
    ).text_frame.text = "Заголовок слайда"
    s1.shapes.add_textbox(
        Inches(limits.content_body.left),
        Inches(limits.content_body.top),
        Inches(limits.content_body.width),
        Inches(limits.content_body.height),
    ).text_frame.text = "• Пункт 1\n• Пункт 2"

    prs.save(str(out))
    print(f"Saved geometry reference deck: {out}")
    print(
        "For named layouts, open in PowerPoint → View → Slide Master → "
        "duplicate layouts and rename to: KPFU Title, KPFU Content, KPFU Content Image"
    )


if __name__ == "__main__":
    main()
