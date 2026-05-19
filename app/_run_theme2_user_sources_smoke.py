"""
Smoke: Theme 2 + mzi (d830) PDF + 2 user conspects as priority sources.
Run from app/: python _run_theme2_user_sources_smoke.py
Requires: USE_MOCK_SERVICES=false, sentence-transformers installed.
"""
import asyncio
import json
import os
import re
import statistics
import time
from pathlib import Path

# Force real embeddings + PPTX before any app imports read env defaults.
os.environ["USE_MOCK_SERVICES"] = "false"
os.environ["PIPELINE_MODE"] = "facet_rag"
os.environ["PACKAGE_PPTX_ENABLED"] = "true"
_tpl = Path(__file__).resolve().parent / "presentation" / "templates" / "kpfu_ru.pptx"
if _tpl.exists():
    os.environ["PACKAGE_PPTX_TEMPLATE_PATH"] = str(_tpl)

from core.config import Settings

import core.config as cfg

cfg.settings = Settings()

from core.model_manager import ModelManager
from literature.processor import get_pdf_processor
from generation.generator_v4 import get_production_content_generator

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "smoke_fixtures" / "user_sources"

THEME = os.getenv(
    "THEME_OVERRIDE",
    "Тема 2. Уязвимости, угрозы, атаки и их классификации",
)
BOOK_ID = os.getenv("BOOK_ID", "d830d4c7ca94")

def _resolve_book_path() -> Path:
    candidates = [
        Path("uploaded_books")
        / "d830d4c7ca941892d83688b33e2295c585ae944d9bcfeab67d95e50f3b64b8e6.pdf",
        Path("app/cache/books/d830d4c7ca94.pdf"),
        Path("..") / "uploaded_books" / "mzi.pdf",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("No book PDF found; expected d830 in uploaded_books or cache")


BOOK_PATH = _resolve_book_path()
OUT = Path("..") / "generated_package_smoke"

CONSPECT_FILES = [
    ("Конспект: тема 2 (полный)", FIXTURES / "theme2_full_10k.md"),
]

GOLD_INTENT_BY_THEME = {
    "Тема 2. Уязвимости, угрозы, атаки и их классификации": {
        "must_include_keywords": [
            "уязвим",
            "угроз",
            "атак",
            "классификац",
            "конфиденциальн",
            "целостн",
            "доступност",
            "cve",
            "cvss",
            "stride",
            "риск",
        ],
        "must_exclude_keywords": [
            "rsa",
            "эйлер",
            "модул",
            "oop",
            "наследован",
            "html",
            "css",
        ],
    },
}


def _load_user_sources() -> list[dict]:
    sources = []
    for title, path in CONSPECT_FILES:
        if not path.exists():
            raise FileNotFoundError(path)
        sources.append({"title": title, "text": path.read_text(encoding="utf-8")})
    return sources


def _load_rpd_data() -> dict:
    """RPD payload with §4.2 lecture_themes + subtopics for facet_rag."""
    base: dict = {
        "subject_title": "Информационная безопасность",
        "academic_degree": "bachelor",
        "profession": "09.03.04 Программная инженерия",
        "department": "Кафедра информационных систем",
        "lecture_themes": [],
    }
    rpd_pdf = ROOT / "РПД ТЕСТ.pdf"
    if rpd_pdf.exists():
        try:
            from literature.processor import get_pdf_processor
            from rpd.section_parser import parse_rpd_sections

            proc = get_pdf_processor()
            ext = proc.extract_text_from_pdf(rpd_pdf)
            text = (ext or {}).get("full_text") or ""
            if text.strip():
                sections = parse_rpd_sections(text)
                fos = sections.get("basic_info") or {}
                if fos.get("subject_title"):
                    base["subject_title"] = fos["subject_title"]
                base["lecture_themes"] = sections.get("lecture_themes") or []
                return base
        except Exception as ex:
            print("WARN: RPD PDF parse failed, using fixture:", ex)

    from rpd.section_parser import parse_lecture_themes_from_section_42

    fixture = """
4.2 Содержание дисциплины (модуля)
Тема 2. Уязвимости, угрозы, атаки и их классификации.
2.1. Уязвимости и их классификация. 2.2. Угрозы и их классификация.
2.3. Атаки и их классификация.
"""
    base["lecture_themes"] = parse_lecture_themes_from_section_42(fixture)
    return base


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
    cfg = GOLD_INTENT_BY_THEME.get(theme, {})
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
            "priority_source_chunks": 0,
            "off_theme_chunk_rate": 1.0,
            "notes": "No selected chunks.",
        }

    informative = 0
    off_theme = 0
    priority_chunks = 0
    for item in selected:
        text = _normalize_text(item.get("text", ""))
        chunk_id = str(item.get("chunk_id", "") or "")
        book = str(item.get("book", "") or "").lower()
        if "priority" in chunk_id or "priority" in book or item.get("priority_source"):
            priority_chunks += 1
        hit_include = any(kw in text for kw in include) if include else True
        hit_exclude = any(kw in text for kw in exclude)
        if hit_include and not hit_exclude:
            informative += 1
        if exclude and (hit_exclude or not hit_include):
            off_theme += 1

    return {
        "theme": theme,
        "selected_chunks": k,
        "priority_source_chunks": priority_chunks,
        "off_theme_chunk_rate": round(off_theme / k, 4) if exclude else 0.0,
        "effective_evidence_density": round(informative / k, 4),
        "gold_intent": cfg,
    }


def _build_grounding_report(generator) -> dict:
    """Aggregate per-facet hallucination diagnostics for threshold calibration."""
    from core.config import settings

    hall_by_facet = dict(getattr(generator, "_last_facet_hallucination_metrics", {}) or {})
    jaccard_min = float(getattr(settings, "facet_section_hallucination_similarity_min", 0.07))
    embedding_min = float(getattr(settings, "facet_section_hallucination_embedding_min", 0.52))
    hall_threshold = float(getattr(settings, "facet_section_hallucination_threshold", 0.25))
    mode = str(getattr(settings, "facet_section_hallucination_grounding_mode", "hybrid"))

    supported_emb: list[float] = []
    unsupported_emb: list[float] = []
    supported_jac: list[float] = []
    unsupported_jac: list[float] = []
    facets_out: list[dict] = []

    for facet, diag in hall_by_facet.items():
        regenerations = int(diag.get("regenerations", 0) or 0)
        hall_rate = float(diag.get("hallucination_rate", 0.0) or 0.0)
        facets_out.append(
            {
                "facet": facet,
                "hallucination_rate": hall_rate,
                "grounded_rate": float(diag.get("grounded_rate", 0.0) or 0.0),
                "regenerations": regenerations,
                "accepted": bool(diag.get("accepted")),
                "sentences_checked": int(diag.get("sentences_checked", 0) or 0),
            }
        )
        for row in diag.get("details") or []:
            jac = float(row.get("jaccard", row.get("similarity", 0.0)) or 0.0)
            emb = float(row.get("embedding", 0.0) or 0.0)
            if row.get("supported"):
                supported_jac.append(jac)
                supported_emb.append(emb)
            else:
                unsupported_jac.append(jac)
                unsupported_emb.append(emb)

    def _pct(vals: list[float], p: float) -> float | None:
        if not vals:
            return None
        vals = sorted(vals)
        idx = min(len(vals) - 1, max(0, int(round((len(vals) - 1) * p))))
        return round(vals[idx], 4)

    suggested_emb = embedding_min
    if supported_emb and unsupported_emb:
        # Between median unsupported and p25 supported — conservative split.
        med_unsup = statistics.median(unsupported_emb)
        p25_sup = _pct(supported_emb, 0.25) or min(supported_emb)
        suggested_emb = round(max(0.35, min(0.72, (med_unsup + p25_sup) / 2)), 3)

    rates = [float(f["hallucination_rate"]) for f in facets_out]
    return {
        "grounding_mode": mode,
        "thresholds": {
            "jaccard_min": jaccard_min,
            "embedding_min": embedding_min,
            "hallucination_threshold": hall_threshold,
        },
        "embedding_backend": getattr(generator, "_smoke_embedding_backend", "unknown"),
        "facet_hallucination_avg": round(sum(rates) / len(rates), 4) if rates else None,
        "facet_hallucination_regenerations_total": sum(
            int(f.get("regenerations", 0) or 0) for f in facets_out
        ),
        "facets": facets_out,
        "score_distributions": {
            "supported_jaccard": {
                "n": len(supported_jac),
                "p50": _pct(supported_jac, 0.5),
                "p75": _pct(supported_jac, 0.75),
            },
            "unsupported_jaccard": {
                "n": len(unsupported_jac),
                "p50": _pct(unsupported_jac, 0.5),
                "p75": _pct(unsupported_jac, 0.75),
            },
            "supported_embedding": {
                "n": len(supported_emb),
                "p25": _pct(supported_emb, 0.25),
                "p50": _pct(supported_emb, 0.5),
                "p75": _pct(supported_emb, 0.75),
            },
            "unsupported_embedding": {
                "n": len(unsupported_emb),
                "p50": _pct(unsupported_emb, 0.5),
                "p75": _pct(unsupported_emb, 0.75),
            },
        },
        "suggested_embedding_min": suggested_emb,
        "calibration_notes": (
            "Raise FACET_SECTION_HALLUCINATION_EMBEDDING_MIN if unsupported p75 overlaps supported p25. "
            "Target facet_hallucination_avg <= hallucination_threshold."
        ),
    }


def _verify_real_embeddings(model_manager) -> str:
    from core.mock_services import MockSentenceTransformer

    emb = getattr(model_manager, "embedding_model", None)
    if emb is None:
        return "missing"
    if isinstance(emb, MockSentenceTransformer):
        return "mock"
    return "sentence_transformers"


async def main():
    user_sources = _load_user_sources()
    t0 = time.time()
    use_mock = os.getenv("USE_MOCK_SERVICES", "false").lower() in ("1", "true", "yes")
    if use_mock:
        print("ERROR: USE_MOCK_SERVICES must be false for calibration smoke")
        return 2

    model_manager = ModelManager(use_mock_services=False)
    await model_manager.initialize()
    backend = _verify_real_embeddings(model_manager)
    if backend != "sentence_transformers":
        print(f"ERROR: expected real embeddings, got backend={backend}")
        return 2
    print("embedding_backend:", backend, "| model:", os.getenv("EMBEDDING_MODEL", "cointegrated/rubert-tiny2"))
    pdf_processor = get_pdf_processor()
    generator = await get_production_content_generator(
        model_manager=model_manager,
        pdf_processor=pdf_processor,
        use_mock=False,
    )
    generator._smoke_embedding_backend = backend

    await generator.initialize_book(str(BOOK_PATH), BOOK_ID)

    rpd_data = _load_rpd_data()
    result = await generator.generate_package_optimized(
        theme=THEME,
        book_ids=[BOOK_ID],
        user_sources=user_sources,
        rpd_data=rpd_data,
    )

    OUT.mkdir(exist_ok=True)
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    pipeline_mode = os.getenv("PIPELINE_MODE", "facet_rag")
    run_dir = OUT / f"{run_stamp}_{pipeline_mode}_theme2_user_src"
    run_dir.mkdir(exist_ok=True)

    (run_dir / "user_sources.json").write_text(
        json.dumps(user_sources, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "rpd_themes.json").write_text(
        json.dumps(rpd_data.get("lecture_themes") or [], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    facet_plan = dict(getattr(generator, "_last_facet_plan", {}) or {})
    if facet_plan:
        (run_dir / "facet_plan.json").write_text(
            json.dumps(facet_plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
    if getattr(result, "presentation_pptx", None):
        (run_dir / "presentation.pptx").write_bytes(result.presentation_pptx)
    slides_json = getattr(result, "presentation_slides_json", "") or ""
    if slides_json.strip():
        (run_dir / "slides.json").write_text(slides_json, encoding="utf-8")
    (run_dir / "review_report.md").write_text(result.review_report_content or "", encoding="utf-8")

    grounding_report = _build_grounding_report(generator)
    (run_dir / "grounding_report.json").write_text(
        json.dumps(grounding_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metrics_payload = {
        "run_stamp": run_stamp,
        "pipeline_mode": pipeline_mode,
        "theme": THEME,
        "book_id": BOOK_ID,
        "book_path": str(BOOK_PATH.resolve()),
        "user_sources_count": len(user_sources),
        "user_source_titles": [s["title"] for s in user_sources],
        "elapsed_seconds": round(time.time() - t0, 2),
        "generation_time_seconds": float(getattr(result, "generation_time_seconds", 0.0) or 0.0),
        "confidence_score": float(getattr(result, "confidence_score", 0.0) or 0.0),
        "warnings": list(getattr(result, "warnings", []) or []),
        "presentation_pptx_bytes": len(getattr(result, "presentation_pptx", None) or b""),
        "presentation_slides_json_chars": len(getattr(result, "presentation_slides_json", "") or ""),
        "step_times": dict(getattr(result, "step_times", {}) or {}),
        "facet_plan_source": facet_plan.get("source"),
        "facet_plan_facets": facet_plan.get("facets"),
        "embedding_backend": backend,
        "grounding_report_summary": {
            "facet_hallucination_avg": grounding_report.get("facet_hallucination_avg"),
            "regenerations_total": grounding_report.get("facet_hallucination_regenerations_total"),
            "suggested_embedding_min": grounding_report.get("suggested_embedding_min"),
        },
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    retrieval_debug = dict(getattr(generator, "_last_retrieval_debug", {}) or {})
    diag = {}
    if retrieval_debug:
        (run_dir / "retrieval_artifacts.json").write_text(
            json.dumps(retrieval_debug, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        diag = _compute_retrieval_diagnostics(THEME, retrieval_debug)
        (run_dir / "retrieval_diagnostics.json").write_text(
            json.dumps(diag, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("OK package generated")
    print("run_dir", run_dir.resolve())
    print("facet_plan", facet_plan.get("source"), facet_plan.get("facets"))
    print("grounding_avg", grounding_report.get("facet_hallucination_avg"))
    print("regenerations", grounding_report.get("facet_hallucination_regenerations_total"))
    print("suggested_EMBEDDING_MIN", grounding_report.get("suggested_embedding_min"))
    print("presentation_pptx_bytes", metrics_payload.get("presentation_pptx_bytes"))
    print("presentation_slides", metrics_payload.get("presentation_slides_json_chars"))
    print("elapsed_sec", round(time.time() - t0, 2))

    await model_manager.cleanup()
    return 0


raise SystemExit(asyncio.run(main()))
