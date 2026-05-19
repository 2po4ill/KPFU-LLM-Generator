"""Tests for RPD section 4.2 / FOS parsing."""

from app.rpd.section_parser import parse_lecture_themes_from_section_42, parse_fos_header_block, parse_rpd_sections

SAMPLE_42 = """
4.2 Содержание дисциплины (модуля)
Тема 1. Основные вопросы защиты информации.
1.1.Введение в информационную безопасность. 1.2. Уровни представления информации.
Тема 2. Уязвимости, угрозы, атаки и их классификации.
2.1. Уязвимости и их классификация. 2.2. Угрозы и их классификация
"""

SAMPLE_FOS = """
Фонд оценочных средств по дисциплине (модулю)
Информационная безопасность
Направление подготовки: 09.03.04 – Программная инженерия
Квалификация выпускника: бакалавр
Форма обучения: очная
Язык обучения: русский
Год начала обучения по образовательной программе: 2023
"""


def test_parse_themes_section_42():
    themes = parse_lecture_themes_from_section_42(SAMPLE_42)
    assert len(themes) >= 2
    assert themes[0]["order"] == 1
    assert "Основные вопросы защиты информации" in themes[0]["title"]
    assert themes[0].get("description")
    assert themes[0].get("subtopics")
    assert themes[0]["subtopics"][0]["code"] == "1.1"


def test_parse_fos_metadata():
    fos = parse_fos_header_block(SAMPLE_FOS)
    assert fos["subject_title"] == "Информационная безопасность"
    assert "09.03.04" in fos["profession"]
    assert fos["academic_degree"] == "bachelor"
    assert fos["study_form"] == "очная"
    assert fos["year"] == 2023


def test_parse_rpd_sections_combined():
    text = SAMPLE_FOS + "\n" + SAMPLE_42
    data = parse_rpd_sections(text)
    assert len(data["lecture_themes"]) >= 2
    assert data["basic_info"]["subject_title"] == "Информационная безопасность"
