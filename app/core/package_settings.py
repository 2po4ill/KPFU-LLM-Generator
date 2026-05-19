"""Temporary override of package-related settings for a single API request."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from core.config import settings


@contextmanager
def package_settings_override(
    *,
    lab_enabled: Optional[bool] = None,
    selfcheck_enabled: Optional[bool] = None,
    pptx_enabled: Optional[bool] = None,
    moodle_enabled: Optional[bool] = None,
    pipeline_mode: Optional[str] = None,
) -> Iterator[None]:
    backup: dict[str, Any] = {}
    patches = {
        "package_lab_enabled": lab_enabled,
        "package_selfcheck_enabled": selfcheck_enabled,
        "package_pptx_enabled": pptx_enabled,
        "package_moodle_xml_enabled": moodle_enabled,
        "pipeline_mode": pipeline_mode,
    }
    try:
        for key, value in patches.items():
            if value is None:
                continue
            backup[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
    finally:
        for key, value in backup.items():
            setattr(settings, key, value)
