import os
import sys

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from generation.generator_v2 import ContentGenerator


class TestTOCSelectionBoundaries:
    def test_build_section_ranges_sorts_dedups_and_caps_span(self):
        generator = ContentGenerator()
        sections = [
            {"number": "2.1", "title": "Second", "page": 30},
            {"number": "1.2", "title": "First part", "page": 12},
            {"number": "1.2", "title": "First part duplicate", "page": 14},
            {"number": "3", "title": "Third", "page": 60},
        ]

        ranged = generator._build_section_ranges(sections, max_section_span=6)

        assert [s["number"] for s in ranged] == ["1.2", "2.1", "3"]
        assert ranged[0]["page"] == 12
        assert ranged[0]["end_page"] == 18  # min(29, 12 + 6)
        assert ranged[1]["end_page"] == 36  # min(59, 30 + 6)
        assert ranged[2]["end_page"] == 66  # last section capped by span

    def test_parse_section_numbers_keeps_only_whitelisted_tokens(self):
        generator = ContentGenerator()
        valid_numbers = {"1.1", "2", "7.4"}
        response = "Selected: 7.4, 2, 999, confidence 0.93"

        parsed = generator._parse_section_numbers(response, valid_numbers)

        assert parsed == ["7.4", "2"]

    def test_parse_section_numbers_handles_zero_response(self):
        generator = ContentGenerator()
        parsed = generator._parse_section_numbers("0", {"1", "2"})

        assert parsed == []

    def test_apply_top_k_pages_caps_result(self):
        generator = ContentGenerator()
        pages = [25, 20, 21, 20, 22, 23]

        capped = generator._apply_top_k_pages(pages, top_k=3)

        assert capped == [20, 21, 22]

    def test_apply_top_k_pages_zero_means_no_cap(self):
        generator = ContentGenerator()
        pages = [7, 3, 3, 5]

        uncapped = generator._apply_top_k_pages(pages, top_k=0)

        assert uncapped == [3, 5, 7]

    def test_select_top_k_pages_by_section_scores_ranks_by_score(self):
        generator = ContentGenerator()
        sections = [
            {"number": "1", "title": "Low relevance", "page": 10, "end_page": 12},
            {"number": "2", "title": "High relevance", "page": 20, "end_page": 22},
        ]
        scores = {"1": 0.2, "2": 0.95}

        pages = generator._select_top_k_pages_by_section_scores(
            sections,
            scores,
            top_k=3,
            buffer_pages=1
        )

        assert pages == [20, 21, 22]
