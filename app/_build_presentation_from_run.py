"""Build presentation.pptx from an existing smoke run lecture.md."""
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["USE_MOCK_SERVICES"] = "false"
os.environ["PACKAGE_PPTX_ENABLED"] = "true"
_tpl = Path(__file__).resolve().parent / "presentation" / "templates" / "kpfu_ru.pptx"
if _tpl.exists():
    os.environ["PACKAGE_PPTX_TEMPLATE_PATH"] = str(_tpl)

from core.config import Settings
import core.config as cfg

cfg.settings = Settings()

from core.model_manager import ModelManager
from generation.generator_v4 import get_production_content_generator


async def main() -> int:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not run_dir or not run_dir.exists():
        print("Usage: python _build_presentation_from_run.py <run_dir>")
        return 2
    lecture_path = run_dir / "lecture.md"
    if not lecture_path.exists():
        print("Missing lecture.md in", run_dir)
        return 2

    theme = "Тема 2. Уязвимости, угрозы, атаки и их классификации"
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        theme = json.loads(metrics_path.read_text(encoding="utf-8")).get("theme") or theme

    rpd_data = {"lecture_themes": []}
    rpd_path = run_dir / "rpd_themes.json"
    if rpd_path.exists():
        rpd_data["lecture_themes"] = json.loads(rpd_path.read_text(encoding="utf-8"))

    mm = ModelManager(use_mock_services=False)
    await mm.initialize()
    gen = await get_production_content_generator(model_manager=mm, use_mock=False)
    book_id = "d830d4c7ca94"
    book_path = Path("uploaded_books") / (
        "d830d4c7ca941892d83688b33e2295c585ae944d9bcfeab67d95e50f3b64b8e6.pdf"
    )
    if book_path.exists():
        await gen.initialize_book(str(book_path), book_id)

    lecture_md = lecture_path.read_text(encoding="utf-8")
    selected_pages = [{"page_number": i, "content": ""} for i in range(7, 16)]
    pres = await gen._build_presentation_from_lecture(
        theme=theme,
        lecture_md=lecture_md,
        selected_pages=selected_pages,
        book_ids=[book_id],
        rpd_data=rpd_data,
        concept_cards=[],
    )
    if pres.slides_json:
        (run_dir / "slides.json").write_text(pres.slides_json, encoding="utf-8")
    if pres.pptx_bytes:
        (run_dir / "presentation.pptx").write_bytes(pres.pptx_bytes)
        print("OK presentation.pptx", len(pres.pptx_bytes), "bytes")
    else:
        print("WARN: empty pptx", pres.warnings)
    if pres.manifest:
        (run_dir / "presentation_manifest.json").write_text(
            json.dumps(pres.manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    await mm.cleanup()
    return 0 if pres.pptx_bytes else 1


raise SystemExit(asyncio.run(main()))
