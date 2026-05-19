"""
Production generator v4.

Single generator runtime:
- TOC-based page selection (migrated from v2 behavior)
- optimized generation pipeline (v3 base)
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

import numpy as np

from core.config import settings
from generation.generator_v3 import OptimizedContentGenerator

logger = logging.getLogger(__name__)


class ProductionContentGenerator(OptimizedContentGenerator):
    """Final production generator with in-class TOC selection + generation."""

    def _add_spaces_to_russian_text(self, text: str) -> str:
        text = re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", text)
        text = re.sub(r"([а-яёА-ЯЁa-zA-Z])(\d)", r"\1 \2", text)
        text = re.sub(r"(\d)([а-яёА-ЯЁa-zA-Z])", r"\1 \2", text)
        return text

    def _build_section_ranges(self, sections: List[Dict[str, Any]], max_section_span: int = 8) -> List[Dict[str, Any]]:
        if not sections:
            return []
        dedup_by_number: Dict[str, Dict[str, Any]] = {}
        for section in sections:
            number = section.get("number")
            page = section.get("page")
            title = section.get("title")
            if number is None or page is None or title is None:
                continue
            existing = dedup_by_number.get(number)
            if existing is None or page < existing["page"]:
                dedup_by_number[number] = {"number": number, "title": title, "page": page}
        ordered = sorted(dedup_by_number.values(), key=lambda s: s["page"])
        for idx, section in enumerate(ordered):
            start = section["page"]
            if idx < len(ordered) - 1:
                next_start = ordered[idx + 1]["page"]
                inferred_end = max(start, next_start - 1)
                section["end_page"] = min(inferred_end, start + max_section_span)
            else:
                section["end_page"] = start + max_section_span
        return ordered

    def _parse_toc_with_regex(self, toc_text: str) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        for raw_line in toc_text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            patterns = [
                r"^(\d+(?:\.\d+)?)\s+(.+?)\s+[.\u2026\s]+(\d+)\s*$",
                r"^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)\s*$",
                r"^(?:Глава|ГЛАВА|Chapter|Раздел)\s+(\d+)\.?\s+(.+?)\s+[.\u2026\s]*(\d+)\s*$",
                r"^§\s*(\d+)\.?\s+(.+?)\s+[.\u2026\s]*(\d+)\s*$",
                r"^(\d+)\.?\s+(.+?)\s+[.\u2026\s]*(\d+)\s*$",
            ]
            for pattern in patterns:
                match = re.match(pattern, line, flags=re.IGNORECASE)
                if not match:
                    continue
                number = match.group(1)
                title = re.sub(r"[.\u2026\s]+$", "", match.group(2).strip())
                title = re.sub(r"\s+", " ", title)
                if len(title) <= 2 or re.match(r"^[.\u2026\s]*$", title):
                    continue
                try:
                    page = int(match.group(3))
                except ValueError:
                    continue
                sections.append({"number": number, "title": self._add_spaces_to_russian_text(title), "page": page})
                break
        return self._build_section_ranges(sections)

    def _parse_section_numbers(self, response_text: str, valid_section_numbers: Optional[set[str]] = None) -> List[str]:
        if not response_text:
            return []
        normalized = response_text.strip()
        if normalized == "0":
            return []
        tokens = [token.strip() for token in re.split(r"[,\s]+", normalized) if token.strip()]
        result: List[str] = []
        seen = set()
        for token in tokens:
            if not re.fullmatch(r"\d+(?:\.\d+)?", token):
                continue
            if valid_section_numbers is not None and token not in valid_section_numbers:
                continue
            if token in seen:
                continue
            seen.add(token)
            result.append(token)
        return result

    def _add_buffer_to_ranges(self, ranges: List[tuple], buffer_pages: int = 1) -> List[int]:
        pages = set()
        for start, end in ranges:
            pages.update(range(start, end + 1))
            pages.update(range(end + 1, end + 1 + buffer_pages))
        return sorted(pages)

    def _apply_top_k_pages(self, pages: List[int], top_k: Optional[int]) -> List[int]:
        unique_sorted_pages = sorted(set(pages))
        if top_k is None or top_k <= 0:
            return unique_sorted_pages
        return unique_sorted_pages[:top_k]

    def _select_top_k_pages_by_section_scores(
        self,
        sections: List[Dict[str, Any]],
        section_scores: Dict[str, float],
        top_k: Optional[int],
        buffer_pages: int = 1,
    ) -> List[int]:
        page_scores: Dict[int, float] = {}
        for section in sections:
            base_score = min(1.0, max(0.0, float(section_scores.get(section["number"], 0.5))))
            start_page = section["page"]
            last_page = section["end_page"] + max(0, buffer_pages)
            for page in range(start_page, last_page + 1):
                score = base_score - 0.01 * max(0, page - start_page)
                prev = page_scores.get(page)
                if prev is None or score > prev:
                    page_scores[page] = score
        ranked = sorted(page_scores.items(), key=lambda item: (-item[1], item[0]))
        ordered_pages = [page for page, _ in ranked]
        if top_k is None or top_k <= 0:
            return ordered_pages
        return ordered_pages[:top_k]

    async def _score_sections_by_theme(self, theme: str, selected_sections: List[Dict[str, Any]]) -> Dict[str, float]:
        if not selected_sections:
            return {}
        if not self.model_manager:
            return {section["number"]: 0.5 for section in selected_sections}
        try:
            lines = [
                f'- {s["number"]}: {s["title"]} (pages {s["page"]}-{s["end_page"]})'
                for s in selected_sections
            ]
            prompt = f"""Тема лекции: "{theme}"
Оцени релевантность каждого раздела.
Формат результата: объект с полем scores, где scores — список
объектов с полями number и score.
Разделы:
{chr(10).join(lines)}
"""
            payload = await self._generate_json_object(
                prompt,
                {"temperature": 0.1, "num_predict": 400},
            )
            parsed: Dict[str, float] = {}
            for item in (payload or {}).get("scores", []):
                number = str(item.get("number", "")).strip()
                try:
                    score = float(item.get("score"))
                except (TypeError, ValueError):
                    continue
                if number:
                    parsed[number] = min(1.0, max(0.0, score))
            for section in selected_sections:
                parsed.setdefault(section["number"], 0.5)
            return parsed
        except Exception as e:
            logger.warning("v4 section scoring fallback: %s", e)
            return {section["number"]: 0.5 for section in selected_sections}

    async def _get_page_numbers_from_toc(self, theme: str, toc_text: str) -> List[int]:
        if not self.model_manager:
            return []
        try:
            sections = self._parse_toc_with_regex(toc_text)
            if not sections:
                return [0]
            formatted_sections = [
                f'{s["number"]} {s["title"]} (pages {s["page"]}-{s["end_page"]})'
                for s in sections
            ]
            llm_model = await self.model_manager.get_llm_model()
            prompt = f"""Тема лекции: "{theme}"
Проанализируй оглавление книги и выбери только релевантные разделы.
Ответ строго:
- "0"
- или номера разделов через запятую (пример: 6,16,26)
Оглавление:
{chr(10).join(formatted_sections)}
"""
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1},
            )
            response_text = str(response.get("response", "") or "").strip()
            if not response_text:
                response_text = str(response.get("thinking", "") or "").strip()
            valid_numbers = {s["number"] for s in sections}
            selected_numbers = self._parse_section_numbers(response_text, valid_numbers)
            selected_sections: List[Dict[str, Any]] = []
            all_ranges = []
            for num in selected_numbers:
                section = next((s for s in sections if s["number"] == num), None)
                if section:
                    selected_sections.append(section)
                    all_ranges.append((section["page"], section["end_page"]))
            if settings.toc_page_top_k_per_book > 0 and selected_sections:
                section_scores = await self._score_sections_by_theme(theme, selected_sections)
                final_pages = self._select_top_k_pages_by_section_scores(
                    selected_sections,
                    section_scores,
                    settings.toc_page_top_k_per_book,
                    buffer_pages=1,
                )
            else:
                final_pages = self._add_buffer_to_ranges(all_ranges, buffer_pages=1)
                final_pages = self._apply_top_k_pages(final_pages, settings.toc_page_top_k_per_book)
            return final_pages if final_pages else [0]
        except Exception as e:
            logger.error("v4 TOC selection failed: %s", e, exc_info=True)
            return []

    async def _extract_claims(self, content: str) -> List[str]:
        try:
            llm_model = await self.model_manager.get_llm_model()
            # Extract claims from the whole lecture in chunks to avoid context overflow.
            chunks: List[str] = []
            chunk_size = 3500
            overlap = 500
            text = content or ""
            start = 0
            while start < len(text):
                end = min(len(text), start + chunk_size)
                chunks.append(text[start:end])
                if end >= len(text):
                    break
                start = max(0, end - overlap)

            all_claims: List[str] = []
            for chunk in chunks:
                prompt = f"""Извлеки фактические технические утверждения из текста.
Формат:
1. ...
2. ...
Текст:
{chunk}
"""
                response = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.1, "num_predict": 1500},
                )
                for line in (response.get("response", "") or "").split("\n"):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                        claim = line.lstrip("0123456789.-•) ").strip()
                        if len(claim) > 20:
                            all_claims.append(claim)

            # Deduplicate while preserving order
            seen = set()
            deduped: List[str] = []
            for c in all_claims:
                key = re.sub(r"\s+", " ", c).strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(c)
            return deduped
        except Exception as e:
            logger.error("v4 claim extraction failed: %s", e)
            return []

    async def _validate_against_pages(self, generated_content: str, selected_pages: List[Dict[str, Any]]) -> float:
        try:
            claims = await self._extract_claims(generated_content)
            self._last_validation_details = []
            self._last_validation_summary = {
                "claims_total": 0,
                "claims_supported": 0,
                "threshold": 0.4,
                "confidence": 0.0,
            }
            if not claims:
                return 0.75
            embedding_model = await self.model_manager.get_embedding_model()
            page_embeddings = embedding_model.encode([p["content"] for p in selected_pages])
            supported = 0
            details: List[Dict[str, Any]] = []
            for claim in claims:
                claim_embedding = embedding_model.encode([claim])[0]
                max_similarity = 0.0
                best_page_number = None
                for idx, page_emb in enumerate(page_embeddings):
                    similarity = np.dot(claim_embedding, page_emb) / (
                        np.linalg.norm(claim_embedding) * np.linalg.norm(page_emb)
                    )
                    if similarity > max_similarity:
                        max_similarity = float(similarity)
                        if 0 <= idx < len(selected_pages):
                            best_page_number = selected_pages[idx].get("page_number")
                is_supported = max_similarity > 0.4
                if is_supported:
                    supported += 1
                details.append(
                    {
                        "claim": claim,
                        "max_cosine_similarity": float(max_similarity),
                        "best_page_number": best_page_number,
                        "supported": bool(is_supported),
                    }
                )
            confidence = supported / len(claims)
            self._last_validation_details = details
            self._last_validation_summary = {
                "claims_total": len(claims),
                "claims_supported": supported,
                "threshold": 0.4,
                "confidence": float(confidence),
            }
            return confidence
        except Exception as e:
            logger.error("v4 validation failed: %s", e, exc_info=True)
            return 0.70

    async def _fgos_formatting(
        self,
        content: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]],
    ) -> tuple[str, List[Dict[str, Any]]]:
        formatted = f"""# ЛЕКЦИЯ ПО ДИСЦИПЛИНЕ "{rpd_data.get('subject_title', '').upper()}"

**Направление подготовки:** {rpd_data.get('profession', '')}
**Уровень образования:** {rpd_data.get('academic_degree', 'bachelor')}
**Кафедра:** {rpd_data.get('department', 'Не указана')}

---

{content}

---

**Дата составления:** {time.strftime('%d.%m.%Y')}
"""
        citations = [
            {"book_title": p["book_title"], "page_number": p["page_number"], "book_id": p["book_id"]}
            for p in selected_pages[:10]
        ]
        return formatted, citations


_production_generator = None


async def get_production_content_generator(
    model_manager=None,
    pdf_processor=None,
    use_mock: bool = False,
) -> ProductionContentGenerator:
    global _production_generator
    if _production_generator is None:
        _production_generator = ProductionContentGenerator(use_mock=use_mock)
        await _production_generator.initialize(model_manager, pdf_processor)
        logger.info("Production generator v4 initialized")
    return _production_generator
