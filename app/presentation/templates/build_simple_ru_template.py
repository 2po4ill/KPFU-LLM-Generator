"""
Create simple_ru.pptx: three slide layouts (Russian names), zero slides in file.

Run from repo root:
  python app/presentation/templates/build_simple_ru_template.py
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from pptx import Presentation

OUT = Path(__file__).resolve().parent / "simple_ru.pptx"

# Built-in layout index -> Russian name (see python-pptx default theme)
RENAME = {
    "Title Slide": "Титульный",
    "Title and Content": "Только текст",
    "Picture with Caption": "Текст с изображением",
}


def _rename_layouts_in_pptx(pptx_path: Path) -> None:
    ns = "http://schemas.openxmlformats.org/presentationml/2006/main"
    ET.register_namespace("p", ns)
    tag = f"{{{ns}}}cSld"

    buf = BytesIO()
    with zipfile.ZipFile(pptx_path, "r") as zin:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("ppt/slideLayouts/slideLayout") and item.filename.endswith(
                    ".xml"
                ):
                    root = ET.fromstring(data)
                    c_sld = root.find(f".//{tag}")
                    if c_sld is not None:
                        old = c_sld.get("name") or ""
                        if old in RENAME:
                            c_sld.set("name", RENAME[old])
                            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)
    pptx_path.write_bytes(buf.getvalue())


def main() -> None:
    prs = Presentation()
    prs.save(OUT)
    _rename_layouts_in_pptx(OUT)
    print("written", OUT, "layouts:", list(RENAME.values()))


if __name__ == "__main__":
    main()
