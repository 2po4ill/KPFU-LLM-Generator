"""RPD subtopics -> facet headings."""

from app.rpd.rpd_facets import (
    facets_from_theme_entry,
    facets_have_rpd_codes,
    find_matching_lecture_theme,
    resolve_facets_from_rpd,
    sort_facets_by_subtopic_code,
)
from app.rpd.section_parser import parse_lecture_themes_from_section_42

SAMPLE_42 = """
4.2 Содержание дисциплины (модуля)
Тема 2. Уязвимости, угрозы, атаки и их классификации.
2.1. Уязвимости и их классификация. 2.2. Угрозы и их классификация.
2.3. Атаки и их классификация.
"""


def test_subtopics_parsed_and_matched():
    themes = parse_lecture_themes_from_section_42(SAMPLE_42)
    assert len(themes) == 1
    subs = themes[0]["subtopics"]
    assert len(subs) == 3
    assert subs[0]["code"] == "2.1"

    rpd = {"lecture_themes": themes}
    facets, meta = resolve_facets_from_rpd(
        rpd, "Тема 2. Уязвимости, угрозы, атаки и их классификации"
    )
    assert meta["source"] == "rpd"
    assert len(facets) == 3
    assert facets[0].startswith("2.1.")


def test_find_theme_by_order():
    themes = parse_lecture_themes_from_section_42(SAMPLE_42)
    hit = find_matching_lecture_theme(themes, "Тема 2. Что угодно")
    assert hit is not None
    assert hit["order"] == 2


def test_facets_from_entry():
    themes = parse_lecture_themes_from_section_42(SAMPLE_42)
    labels = facets_from_theme_entry(themes[0])
    assert "2.3." in labels[2]


def test_sort_facets_by_subtopic_code():
    shuffled = [
        "2.3. Атаки и их классификация",
        "2.1. Уязвимости и их классификация",
        "2.2. Угрозы и их классификация",
    ]
    ordered = sort_facets_by_subtopic_code(shuffled)
    assert ordered[0].startswith("2.1")
    assert ordered[1].startswith("2.2")
    assert ordered[2].startswith("2.3")
    assert facets_have_rpd_codes(ordered)


def test_filter_preserves_rpd_order_simulation():
    """Regression: similarity sort must not put 2.3 before 2.1."""
    facets, _ = resolve_facets_from_rpd(
        {"lecture_themes": parse_lecture_themes_from_section_42(SAMPLE_42)},
        "Тема 2. Уязвимости, угрозы, атаки и их классификации",
    )
    assert facets[0].startswith("2.1")
    assert facets[1].startswith("2.2")
    assert facets[2].startswith("2.3")
