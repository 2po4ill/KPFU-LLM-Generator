"""Cache and serve presentation slide images for UI preview."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

_PREVIEW_ROOT = Path("app/cache/package_previews")
_STORE: Dict[str, Dict[str, Any]] = {}

_SKIP_IMAGE_KINDS = frozenset({"none", "placeholder", "page_snapshot"})


def preview_key(fingerprint: str, theme_title: str) -> str:
    raw = f"{fingerprint}::{theme_title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def preview_dir(fingerprint: str, theme_title: str) -> Path:
    return _PREVIEW_ROOT / preview_key(fingerprint, theme_title)


def preview_image_url(fingerprint: str, theme_title: str, filename: str) -> str:
    fp_q = quote(fingerprint, safe="")
    th_q = quote(theme_title, safe="")
    return (
        f"/rpd/presentation-preview/image?fingerprint={fp_q}"
        f"&theme_title={th_q}&file={quote(filename, safe='')}"
    )


def store_presentation_preview(
    fingerprint: str,
    theme_title: str,
    *,
    slides: List[Dict[str, Any]],
    resolved_paths: List[Optional[str]],
    manifest_entries: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    key = preview_key(fingerprint, theme_title)
    dest = preview_dir(fingerprint, theme_title)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)

    content_idx = 0
    manifest_idx = 0
    preview_slides: List[Dict[str, Any]] = []
    figure_n = 0

    for slide in slides:
        layout = str(slide.get("layout") or "content").lower()
        entry: Dict[str, Any] = {
            "layout": layout,
            "title": slide.get("title") or "",
            "subtitle": slide.get("subtitle") or "",
            "bullets": list(slide.get("bullets") or [])[:8],
            "image_url": None,
            "image_kind": None,
            "image_caption": str(slide.get("image_caption") or "").strip(),
            "figure_number": None,
        }
        if layout == "title":
            preview_slides.append(entry)
            continue

        man: Dict[str, Any] = {}
        if manifest_entries and manifest_idx < len(manifest_entries):
            man = dict(manifest_entries[manifest_idx] or {})
            manifest_idx += 1

        img_kind = str(man.get("image_kind") or slide.get("image_kind") or "").lower()
        img_path = None
        if content_idx < len(resolved_paths):
            img_path = resolved_paths[content_idx]
            content_idx += 1

        caption = entry["image_caption"] or str(man.get("image_note") or "").strip()
        if img_kind not in _SKIP_IMAGE_KINDS and img_path and Path(img_path).exists():
            ext = Path(img_path).suffix.lower() or ".png"
            figure_n += 1
            name = f"slide_{len(preview_slides):03d}{ext}"
            shutil.copy2(img_path, dest / name)
            entry["image_url"] = preview_image_url(fingerprint, theme_title, name)
            entry["image_kind"] = img_kind if img_kind and img_kind != "none" else "figure"
            entry["figure_number"] = figure_n
            if caption and not entry["image_caption"]:
                entry["image_caption"] = caption
        else:
            entry["image_kind"] = "none"

        preview_slides.append(entry)

    payload = {
        "fingerprint": fingerprint,
        "theme_title": theme_title,
        "slides": preview_slides,
        "slide_count": len(preview_slides),
    }
    (dest / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _STORE[key] = {"dir": str(dest), "manifest": payload}
    return payload


def save_user_slide_image(
    fingerprint: str,
    theme_title: str,
    slide_index: int,
    src_path: Path,
) -> Dict[str, Any]:
    """Replace or set image for a slide in the preview cache (expert upload)."""
    dest = preview_dir(fingerprint, theme_title)
    dest.mkdir(parents=True, exist_ok=True)
    ext = src_path.suffix.lower() if src_path.suffix else ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        ext = ".png"
    name = f"user_slide_{int(slide_index):03d}{ext}"
    shutil.copy2(src_path, dest / name)

    manifest_path = dest / "manifest.json"
    manifest: Dict[str, Any] = {"slides": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    slides = list(manifest.get("slides") or [])
    if slide_index < 0 or slide_index >= len(slides):
        raise ValueError("slide_index out of range")

    figure_n = 0
    for i, s in enumerate(slides):
        if str(s.get("layout") or "").lower() == "title":
            continue
        if i == slide_index or s.get("image_url"):
            if i == slide_index:
                figure_n += 1
                s["image_url"] = preview_image_url(fingerprint, theme_title, name)
                s["image_kind"] = "user"
                s["figure_number"] = figure_n
            elif s.get("image_url") and str(s.get("image_kind") or "") not in _SKIP_IMAGE_KINDS:
                figure_n += 1
                s["figure_number"] = figure_n
        elif s.get("image_url"):
            pass

    # Re-number all figures in order
    n = 0
    for s in slides:
        if str(s.get("layout") or "").lower() == "title":
            s["figure_number"] = None
            continue
        if s.get("image_url") and str(s.get("image_kind") or "none") not in _SKIP_IMAGE_KINDS:
            n += 1
            s["figure_number"] = n
        else:
            s["figure_number"] = None

    target = slides[slide_index]
    target["image_url"] = preview_image_url(fingerprint, theme_title, name)
    target["image_kind"] = "user"

    manifest["slides"] = slides
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    key = preview_key(fingerprint, theme_title)
    _STORE[key] = {"dir": str(dest), "manifest": manifest}

    return {
        "slide_index": slide_index,
        "image_url": target["image_url"],
        "image_kind": "user",
        "figure_number": target.get("figure_number"),
        "image_caption": target.get("image_caption") or "",
    }


def clear_slide_image(fingerprint: str, theme_title: str, slide_index: int) -> Dict[str, Any]:
    manifest_path = preview_dir(fingerprint, theme_title) / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("Preview not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    slides = list(manifest.get("slides") or [])
    if slide_index < 0 or slide_index >= len(slides):
        raise ValueError("slide_index out of range")
    slides[slide_index]["image_url"] = None
    slides[slide_index]["image_kind"] = "none"
    slides[slide_index]["figure_number"] = None
    n = 0
    for s in slides:
        if str(s.get("layout") or "").lower() == "title":
            continue
        if s.get("image_url") and str(s.get("image_kind") or "none") not in _SKIP_IMAGE_KINDS:
            n += 1
            s["figure_number"] = n
        else:
            s["figure_number"] = None
    manifest["slides"] = slides
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"slide_index": slide_index, "image_url": None, "image_kind": "none"}


def get_preview_manifest(fingerprint: str, theme_title: str) -> Optional[Dict[str, Any]]:
    key = preview_key(fingerprint, theme_title)
    cached = _STORE.get(key)
    if cached:
        return cached.get("manifest")
    manifest_path = _PREVIEW_ROOT / key / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return None


def resolve_preview_image(fingerprint: str, theme_title: str, file: str) -> Optional[Path]:
    key = preview_key(fingerprint, theme_title)
    safe = Path(file).name
    path = _PREVIEW_ROOT / key / safe
    if path.exists() and path.is_file():
        return path
    return None
