"""
Download direct PDF links with SHA-256 dedup and register in app/cache/books.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _slug_from_url(url: str, max_len: int = 80) -> str:
    tail = url.rstrip("/").split("/")[-1]
    tail = _SAFE_NAME_RE.sub("_", tail)[:max_len]
    return tail or "source"


async def download_and_register_direct_pdf(
    url: str,
    *,
    model_manager: Any,
    fingerprint: Optional[str] = None,
    title: Optional[str] = None,
    authors: Optional[str] = None,
) -> Dict[str, Any]:
    from literature.processor import get_pdf_processor
    from literature.embeddings import get_embedding_service
    from core.toc_cache import get_optimized_pdf_processor

    uploaded_root = Path(settings.uploaded_books_dir)
    books_dir = Path(settings.books_cache_dir)
    uploaded_root.mkdir(parents=True, exist_ok=True)
    books_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = settings.source_download_max_bytes
    timeout = httpx.Timeout(settings.source_download_timeout_seconds)

    sha = hashlib.sha256()
    total = 0
    content_type: Optional[str] = None
    tmp_path: Optional[Path] = None

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.source_download_user_agent},
        ) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp_path = Path(tmp.name)
                    async for chunk in resp.aiter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError(
                                f"Download exceeds limit ({max_bytes} bytes)"
                            )
                        sha.update(chunk)
                        tmp.write(chunk)

        digest = sha.hexdigest()
        dest_storage = uploaded_root / f"{digest}.pdf"

        ct_ok = content_type in ("application/pdf", "application/x-pdf", "")
        path_ok = url.lower().split("?")[0].endswith(".pdf")
        if not ct_ok and not path_ok and content_type.startswith("text/"):
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            return {
                "success": False,
                "book_id": None,
                "sha256": digest,
                "storage_relpath": None,
                "duplicate": False,
                "error": f"Not a PDF (content-type={content_type or 'unknown'})",
            }

        duplicate = dest_storage.exists()
        if tmp_path:
            if not duplicate:
                shutil.move(str(tmp_path), str(dest_storage))
            else:
                tmp_path.unlink(missing_ok=True)

        book_id = digest[:12]
        cache_path = books_dir / f"{book_id}.pdf"
        if not cache_path.exists() or cache_path.stat().st_size != dest_storage.stat().st_size:
            shutil.copy2(dest_storage, cache_path)

        slug = _slug_from_url(url)
        title_f = title or slug
        authors_f = authors or "Unknown"

        pdf_processor = get_pdf_processor()
        processing_result = await pdf_processor.process_book(cache_path, book_id)
        if not processing_result.get("success"):
            err = processing_result.get("error", "PDF processing failed")
            return {
                "success": False,
                "book_id": book_id,
                "sha256": digest,
                "storage_relpath": str(dest_storage.as_posix()),
                "duplicate": duplicate,
                "error": str(err),
            }

        use_mock = getattr(model_manager, "use_mock_services", False)
        embedding_service = await get_embedding_service(
            model_manager=model_manager,
            use_mock=use_mock,
        )
        book_metadata = {
            "title": title_f,
            "authors": authors_f,
            "year": None,
            "fingerprint": fingerprint,
            "source_url": url,
        }
        await asyncio.to_thread(
            embedding_service.add_chunks_to_vector_store,
            processing_result["chunks"],
            book_metadata,
        )

        optimized_processor = await get_optimized_pdf_processor(pdf_processor)
        await optimized_processor.initialize_book(cache_path, book_id)

        return {
            "success": True,
            "book_id": book_id,
            "sha256": digest,
            "storage_relpath": str(dest_storage.as_posix()),
            "duplicate": duplicate,
            "error": None,
        }

    except Exception as e:
        logger.exception("direct PDF download failed: %s", url)
        if tmp_path:
            tmp_path.unlink(missing_ok=True)
        return {
            "success": False,
            "book_id": None,
            "sha256": None,
            "storage_relpath": None,
            "duplicate": False,
            "error": str(e),
        }
