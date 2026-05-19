"""
Smoke test for package generation:
lecture + lab + self-check in one pass.
"""
import asyncio
import time
from pathlib import Path

from app.core.model_manager import ModelManager
from app.literature.processor import get_pdf_processor
from app.generation.generator_v3 import get_optimized_content_generator


async def run_test():
    theme = "Работа со строками"
    book_path = "Изучаем_Питон.pdf"
    book_id = "izuchaem_python_pkg"

    print("=" * 80)
    print("PACKAGE GENERATION SMOKE TEST")
    print("=" * 80)
    print(f"Theme: {theme}")
    print(f"Book: {book_path}")
    print("\n[STEP 1/4] Init models + generator")

    model_manager = ModelManager(use_mock_services=False)
    await model_manager.initialize()
    pdf_processor = get_pdf_processor()
    generator = await get_optimized_content_generator()
    await generator.initialize(model_manager, pdf_processor)

    print("\n[STEP 2/4] Initialize book cache")
    init_result = await generator.initialize_book(book_path, book_id)
    if not init_result.get("success"):
        print(f"Book init failed: {init_result}")
        return 1

    print("Book initialized.")
    print("\n[STEP 3/4] Generate package (watch [CHECKPOINT x/y] logs)")
    started = time.time()
    result = await generator.generate_package_optimized(
        theme=theme,
        book_ids=[book_id],
        rpd_data={
            "subject_title": "Курс: Программная инженерия",
            "academic_degree": "bachelor",
            "profession": "Программная инженерия",
            "department": "Кафедра информационных систем",
        },
    )
    elapsed = time.time() - started

    if not result.success:
        print(f"FAILED: {result.errors}")
        return 2

    out_dir = Path("generated_package_smoke")
    out_dir.mkdir(exist_ok=True)

    lecture_file = out_dir / "lecture_smoke.md"
    lab_file = out_dir / "lab_smoke.md"
    selfcheck_file = out_dir / "selfcheck_smoke.md"
    review_file = out_dir / "review_report_smoke.md"
    moodle_xml_file = out_dir / "questions_moodle.xml"

    lecture_file.write_text(result.lecture_content, encoding="utf-8")
    lab_file.write_text(result.lab_content, encoding="utf-8")
    selfcheck_file.write_text(result.selfcheck_content, encoding="utf-8")
    review_file.write_text(result.review_report_content, encoding="utf-8")
    if getattr(result, "moodle_questions_xml", ""):
        moodle_xml_file.write_text(result.moodle_questions_xml, encoding="utf-8")

    print("\n[STEP 4/4] Save artifacts")
    print("\nSUCCESS")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Lecture words: {len(result.lecture_content.split())}")
    print(f"Lab words: {len(result.lab_content.split())}")
    print(f"Self-check words: {len(result.selfcheck_content.split())}")
    print(f"Concept cards: {len(result.concept_cards)}")
    if getattr(result, "step_times", None):
        print("Step timings:")
        for k, v in sorted(result.step_times.items()):
            try:
                print(f"  {k}: {float(v):.2f}s")
            except Exception:
                print(f"  {k}: {v}")
    print(f"Saved: {lecture_file}")
    print(f"Saved: {lab_file}")
    print(f"Saved: {selfcheck_file}")
    print(f"Saved: {review_file}")
    if getattr(result, "moodle_questions_xml", ""):
        print(f"Saved: {moodle_xml_file}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_test()))

