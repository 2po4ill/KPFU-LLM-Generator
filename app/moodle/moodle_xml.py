import html
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class MultiChoiceQuestion:
    number: int
    text: str
    choices: List[str]  # ordered a,b,c,d
    correct_index: int  # 0..3


def _xml_text(text: str) -> str:
    # Moodle XML accepts HTML inside CDATA; still good to normalize.
    return (text or "").strip()


def _as_html(text: str) -> str:
    # Minimal: escape only; we do not render Markdown here.
    # Moodle will show this as plain text; safe and predictable.
    return html.escape(_xml_text(text))


def _extract_answer_key_letters(selfcheck_md: str) -> Dict[int, str]:
    """
    Parse answer key block for test questions.
    Expected patterns:
    - `1.  **б)** ...`
    - `1. **b)** ...`
    Returns mapping: question_number -> letter (a/b/c/d or а/б/в/г).
    """
    md = selfcheck_md or ""
    # Find key section start
    m = re.search(r"^##\s+Ключ\s+ответов[\s\S]*?$", md, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return {}
    key = md[m.start() :]
    out: Dict[int, str] = {}
    line_re = re.compile(r"^\s*(\d+)\.\s*\*\*?\s*([a-dа-бвг])\)\*?\*", flags=re.I)
    for line in key.splitlines():
        mm = line_re.match(line)
        if not mm:
            continue
        n = int(mm.group(1))
        letter = mm.group(2).lower()
        out[n] = letter
    return out


def _letter_to_index(letter: str) -> Optional[int]:
    if not letter:
        return None
    letter = letter.lower().strip()
    ru = {"а": 0, "б": 1, "в": 2, "г": 3}
    en = {"a": 0, "b": 1, "c": 2, "d": 3}
    return ru.get(letter, en.get(letter))


def extract_first_multichoice_questions(
    selfcheck_md: str, limit: int = 7
) -> List[MultiChoiceQuestion]:
    """
    Extract first N single-choice questions from the self-check markdown.
    We assume each question has 4 choices labeled `а) б) в) г)` (or a/b/c/d).
    """
    md = selfcheck_md or ""
    key_letters = _extract_answer_key_letters(md)

    # Narrow to "Тестовые вопросы" section to avoid short answers/mini tasks.
    sec_m = re.search(
        r"^##\s+Тестовые\s+вопросы[\s\S]*?(?=^##\s+Вопросы\s+с\s+коротким\s+ответом|\Z)",
        md,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    section = sec_m.group(0) if sec_m else md

    q_re = re.compile(r"^\s*(\d+)\.\s+\*\*(.+?)\*\*\s*$")
    choice_re = re.compile(r"^\s*([a-dа-бвг])\)\s+(.*)\s*$", flags=re.I)

    questions: List[MultiChoiceQuestion] = []
    lines = section.splitlines()
    i = 0
    while i < len(lines) and len(questions) < limit:
        line = lines[i]
        qm = q_re.match(line)
        if not qm:
            i += 1
            continue
        n = int(qm.group(1))
        qtext = qm.group(2).strip()
        choices: List[str] = []
        j = i + 1
        while j < len(lines) and len(choices) < 4:
            cm = choice_re.match(lines[j])
            if cm:
                choices.append(cm.group(2).strip())
            j += 1

        if len(choices) == 4:
            letter = key_letters.get(n, "")
            idx = _letter_to_index(letter)
            if idx is None:
                idx = 0
            questions.append(
                MultiChoiceQuestion(
                    number=n, text=qtext, choices=choices, correct_index=idx
                )
            )
        i = j

    return questions


def build_moodle_multichoice_xml(
    *, quiz_name: str, selfcheck_md: str, limit: int = 7
) -> str:
    """
    Build Moodle Question XML with N multichoice questions.
    Import path in Moodle: Question bank -> Import -> Moodle XML.
    """
    questions = extract_first_multichoice_questions(selfcheck_md, limit=limit)

    parts: List[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append("<quiz>")
    # Category stub (optional but useful)
    cat = f"$course$/Generated/{quiz_name}"
    parts.append('  <question type="category">')
    parts.append("    <category>")
    parts.append(f"      <text>{html.escape(cat)}</text>")
    parts.append("    </category>")
    parts.append("  </question>")

    for q in questions:
        parts.append('  <question type="multichoice">')
        parts.append("    <name>")
        parts.append(f"      <text>{html.escape(f'{quiz_name} Q{q.number}')}</text>")
        parts.append("    </name>")
        parts.append('    <questiontext format="html">')
        parts.append(f"      <text><![CDATA[{_as_html(q.text)}]]></text>")
        parts.append("    </questiontext>")
        parts.append("    <generalfeedback format=\"html\"><text></text></generalfeedback>")
        parts.append("    <defaultgrade>1.0000000</defaultgrade>")
        parts.append("    <penalty>0.3333333</penalty>")
        parts.append("    <hidden>0</hidden>")
        parts.append("    <single>true</single>")
        parts.append("    <shuffleanswers>true</shuffleanswers>")
        parts.append("    <answernumbering>abc</answernumbering>")

        for idx, choice in enumerate(q.choices):
            frac = "100" if idx == q.correct_index else "0"
            parts.append(f'    <answer fraction="{frac}" format="html">')
            parts.append(f"      <text><![CDATA[{_as_html(choice)}]]></text>")
            parts.append("      <feedback format=\"html\"><text></text></feedback>")
            parts.append("    </answer>")

        parts.append("  </question>")

    parts.append("</quiz>")
    return "\n".join(parts) + "\n"

