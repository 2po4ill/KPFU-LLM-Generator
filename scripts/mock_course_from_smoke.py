import re
import shutil
from pathlib import Path


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9а-яё]+", "-", s, flags=re.I)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "theme"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    smoke = root / "generated_package_smoke"
    if not smoke.exists():
        raise SystemExit(f"Missing folder: {smoke}")

    lecture_src = smoke / "lecture_smoke.md"
    lab_src = smoke / "lab_smoke.md"
    selfcheck_src = smoke / "selfcheck_smoke.md"
    qxml_src = smoke / "questions_moodle.xml"

    missing = [p for p in [lecture_src, lab_src, selfcheck_src] if not p.exists()]
    if missing:
        raise SystemExit(f"Missing smoke artifacts: {missing}")

    title = "Работа со строками"
    try:
        txt = selfcheck_src.read_text(encoding="utf-8")
        m = re.search(r"^#\s+Самопроверка:\s*(.+)$", txt, flags=re.MULTILINE)
        if m:
            title = m.group(1).strip()
    except Exception:
        pass

    out_root = root / "generated_course_packages"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    for i in range(1, 13):
        d = out_root / f"{i:02d}-{slug}"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lecture_src, d / "lecture.md")
        shutil.copyfile(lab_src, d / "lab.md")
        shutil.copyfile(selfcheck_src, d / "selfcheck.md")
        if qxml_src.exists():
            shutil.copyfile(qxml_src, d / "questions_moodle.xml")

    print(f"Built mock course: {out_root} (themes=12, from={smoke})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

