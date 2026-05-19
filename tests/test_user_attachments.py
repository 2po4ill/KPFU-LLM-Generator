"""Tests for user attachment sources."""

from app.sources.user_attachments import normalize_user_sources, user_sources_to_pages


def test_normalize_and_pages():
    sources = normalize_user_sources(
        [{"title": "Notes", "text": "RSA — асимметричное шифрование."}]
    )
    assert len(sources) == 1
    pages = user_sources_to_pages(sources, theme="RSA")
    assert len(pages) == 1
    assert pages[0]["priority_source"] is True
    assert pages[0]["toc_bypass"] is True
    assert "RSA" in pages[0]["content"]
