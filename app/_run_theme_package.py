import asyncio
import os
import json
import time
import re
import shutil
from pathlib import Path

from core.model_manager import ModelManager
from literature.processor import get_pdf_processor
from generation.generator_v4 import get_production_content_generator

THEME = os.getenv("THEME_OVERRIDE", "Основные вопросы защиты информации.")
BOOK_PATH = Path("..") / "uploaded_books" / "mzi.pdf"
BOOK_ID = "mzi_linux_sec"
OUT = Path("..") / "generated_package_smoke"

GOLD_INTENT_BY_THEME = {
    "RSA": {
        "must_include_keywords": [
            "rsa",
            "открыт",
            "закрыт",
            "ключ",
            "модул",
            "шифр",
            "теорема эйлера",
            "ферма",
        ],
        "must_exclude_keywords": [
            "oop",
            "наследован",
            "инкапсуляц",
            "полиморф",
            "html",
            "css",
            "javascript",
        ],
    }
}


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-яё0-9]+", _normalize_text(text)))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _compute_retrieval_diagnostics(theme: str, retrieval_debug: dict) -> dict:
    cfg = GOLD_INTENT_BY_THEME.get(theme, GOLD_INTENT_BY_THEME.get("RSA", {}))
    include = [k.lower() for k in cfg.get("must_include_keywords", [])]
    exclude = [k.lower() for k in cfg.get("must_exclude_keywords", [])]

    selected = []
    for concept in retrieval_debug.get("concepts", []):
        selected.extend(concept.get("selected", []))
    k = len(selected)
    if k == 0:
        return {
            "theme": theme,
            "selected_chunks": 0,
            "off_theme_chunk_rate": 1.0,
            "redundancy_ratio": 1.0,
            "effective_evidence_density": 0.0,
            "notes": "No selected chunks available for diagnostics.",
        }

    informative = 0
    off_theme = 0
    token_sets: list[set[str]] = []
    for item in selected:
        text = _normalize_text(item.get("text", ""))
        hit_include = any(k in text for k in include)
        hit_exclude = any(k in text for k in exclude)
        if hit_include and not hit_exclude:
            informative += 1
        if hit_exclude or not hit_include:
            off_theme += 1
        token_sets.append(_token_set(text))

    duplicate_pairs = 0
    total_pairs = 0
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            total_pairs += 1
            if _jaccard(token_sets[i], token_sets[j]) >= 0.85:
                duplicate_pairs += 1
    redundancy_ratio = (duplicate_pairs / total_pairs) if total_pairs else 0.0

    return {
        "theme": theme,
        "selected_chunks": k,
        "off_theme_chunk_rate": round(off_theme / k, 4),
        "redundancy_ratio": round(redundancy_ratio, 4),
        "effective_evidence_density": round(informative / k, 4),
        "gold_intent": cfg,
    }


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[\.\!\?])\s+", text or "")
    return [s.strip() for s in raw if len(s.strip()) >= 40]


def _compute_lecture_source_alignment(lecture_text: str, selected_pages: list[dict]) -> dict:
    lecture_sentences = _split_sentences(lecture_text)
    page_tokens: dict[int, set[str]] = {}
    for p in selected_pages:
        page_num = int(p.get("page_number", 0) or 0)
        page_tokens[page_num] = _token_set(p.get("content", "") or "")

    supported = 0
    unsupported = 0
    details = []
    for sent in lecture_sentences[:220]:
        s_tokens = _token_set(sent)
        best_page = 0
        best_score = 0.0
        for pg, tokens in page_tokens.items():
            score = _jaccard(s_tokens, tokens)
            if score > best_score:
                best_score = score
                best_page = pg
        is_supported = best_score >= 0.08
        if is_supported:
            supported += 1
        else:
            unsupported += 1
        details.append(
            {
                "sentence": sent[:400],
                "best_page": best_page,
                "similarity": round(best_score, 4),
                "supported": is_supported,
            }
        )

    total = max(1, supported + unsupported)
    return {
        "sentences_checked": supported + unsupported,
        "supported_sentences": supported,
        "unsupported_sentences": unsupported,
        "supported_rate": round(supported / total, 4),
        "selected_pages": sorted([int(p.get("page_number", 0) or 0) for p in selected_pages]),
        "details": details,
    }

async def main():
    t0 = time.time()
    model_manager = ModelManager(use_mock_services=False)
    await model_manager.initialize()
    pdf_processor = get_pdf_processor()
    generator = await get_production_content_generator(
        model_manager=model_manager,
        pdf_processor=pdf_processor,
        use_mock=False,
    )

    await generator.initialize_book(str(BOOK_PATH), BOOK_ID)

    result = await generator.generate_package_optimized(
        theme=THEME,
        book_ids=[BOOK_ID],
        rpd_data={
            "subject_title": "Информационная безопасность",
            "academic_degree": "bachelor",
            "profession": "09.03.04 Программная инженерия",
            "department": "Кафедра информационных систем",
        },
    )

    OUT.mkdir(exist_ok=True)
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    pipeline_mode = os.getenv("PIPELINE_MODE", "claims")
    run_dir = OUT / f"{run_stamp}_{pipeline_mode}"
    run_dir.mkdir(exist_ok=True)

    if not result.success:
        print("FAILED", result.errors)
        await model_manager.cleanup()
        return 2

    (run_dir / "lecture.md").write_text(result.lecture_content or "", encoding="utf-8")
    prov_lecture = getattr(generator, "_last_lecture_with_provenance", None)
    if prov_lecture and prov_lecture != (result.lecture_content or ""):
        (run_dir / "lecture_provenance.md").write_text(prov_lecture, encoding="utf-8")
    if (result.lab_content or "").strip():
        (run_dir / "lab.md").write_text(result.lab_content, encoding="utf-8")
    if (result.selfcheck_content or "").strip():
        (run_dir / "selfcheck.md").write_text(result.selfcheck_content, encoding="utf-8")
    (run_dir / "review_report.md").write_text(result.review_report_content or "", encoding="utf-8")
    if getattr(result, "moodle_questions_xml", ""):
        (run_dir / "questions_moodle.xml").write_text(result.moodle_questions_xml, encoding="utf-8")
    if getattr(result, "presentation_slides_json", ""):
        (run_dir / "slides.json").write_text(result.presentation_slides_json, encoding="utf-8")
    pptx_bytes = getattr(result, "presentation_pptx", None) or b""
    slides_path = run_dir / "slides.json"
    if (not pptx_bytes) and slides_path.exists():
        try:
            from _rebuild_presentation import rebuild as rebuild_presentation

            rebuild_presentation(run_dir, theme=THEME)
            pptx_bytes = (run_dir / "presentation.pptx").read_bytes()
        except Exception as ex:
            print("WARN: pptx rebuild from slides.json failed:", ex)
    if pptx_bytes:
        (run_dir / "presentation.pptx").write_bytes(pptx_bytes)
    pres_assets_src = getattr(generator, "_last_presentation_assets_dir", None)
    if pres_assets_src and Path(pres_assets_src).exists():
        dest = run_dir / "presentation_assets"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(pres_assets_src, dest)

    metrics_payload = {
        "run_stamp": run_stamp,
        "pipeline_mode": pipeline_mode,
        "llm_model": os.getenv("LLM_MODEL", ""),
        "package_lab_enabled": os.getenv("PACKAGE_LAB_ENABLED", "true"),
        "package_selfcheck_enabled": os.getenv("PACKAGE_SELFCHECK_ENABLED", "true"),
        "package_pptx_enabled": os.getenv("PACKAGE_PPTX_ENABLED", "false"),
        "package_moodle_xml_enabled": os.getenv("PACKAGE_MOODLE_XML_ENABLED", "true"),
        "theme": THEME,
        "book_id": BOOK_ID,
        "book_path": str(BOOK_PATH),
        "elapsed_seconds": round(time.time() - t0, 2),
        "generation_time_seconds": float(getattr(result, "generation_time_seconds", 0.0) or 0.0),
        "confidence_score": float(getattr(result, "confidence_score", 0.0) or 0.0),
        "warnings": list(getattr(result, "warnings", []) or []),
        "errors": list(getattr(result, "errors", []) or []),
        "step_times": dict(getattr(result, "step_times", {}) or {}),
        "citations_count": len(getattr(result, "citations", []) or []),
        "sources_used_count": len(getattr(result, "sources_used", []) or []),
        "concept_cards_count": len(getattr(result, "concept_cards", []) or []),
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    validation_details = list(getattr(generator, "_last_validation_details", []) or [])
    validation_summary = dict(getattr(generator, "_last_validation_summary", {}) or {})
    (run_dir / "verification_claims.json").write_text(
        json.dumps(
            {
                "summary": validation_summary,
                "claims": validation_details,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    retrieval_debug = dict(getattr(generator, "_last_retrieval_debug", {}) or {})
    if retrieval_debug:
        (run_dir / "retrieval_artifacts.json").write_text(
            json.dumps(retrieval_debug, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        retrieval_diagnostics = _compute_retrieval_diagnostics(THEME, retrieval_debug)
        (run_dir / "retrieval_diagnostics.json").write_text(
            json.dumps(retrieval_diagnostics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    selected_pages = list(getattr(generator, "_last_selected_pages", []) or [])
    if selected_pages:
        pages_payload = [
            {
                "page_number": int(p.get("page_number", 0) or 0),
                "book_title": str(p.get("book_title", "") or ""),
                "content_preview": re.sub(r"\s+", " ", (p.get("content", "") or "")).strip()[:500],
            }
            for p in selected_pages
        ]
        (run_dir / "selected_pages_snapshot.json").write_text(
            json.dumps(pages_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        alignment = _compute_lecture_source_alignment(result.lecture_content or "", selected_pages)
        (run_dir / "lecture_source_alignment.json").write_text(
            json.dumps(alignment, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    facet_hallucination = dict(getattr(generator, "_last_facet_hallucination_metrics", {}) or {})
    if facet_hallucination:
        (run_dir / "facet_hallucination_metrics.json").write_text(
            json.dumps(facet_hallucination, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("OK package generated")
    print("run_dir", run_dir)
    print("elapsed_sec", round(time.time()-t0, 2))
    print("step_times", result.step_times)

    await model_manager.cleanup()
    return 0

raise SystemExit(asyncio.run(main()))
