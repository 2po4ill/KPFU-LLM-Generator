"""
Render Mermaid diagram to PNG when mermaid-cli (mmdc) is available.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from presentation.slide_mermaid import sanitize_mermaid_for_cli

logger = logging.getLogger(__name__)


def render_mermaid_to_png(mermaid_source: str, out_path: Path, *, timeout_seconds: float = 45.0) -> Optional[Path]:
    source = sanitize_mermaid_for_cli(mermaid_source or "")
    if not source:
        return None
    mmdc = shutil.which("mmdc")
    if not mmdc:
        logger.info("mmdc not found; mermaid image skipped")
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        mmd_file = Path(tmp) / "diagram.mmd"
        mmd_file.write_text(source, encoding="utf-8")
        try:
            out_abs = out_path.resolve()
            subprocess.run(
                [mmdc, "-i", str(mmd_file), "-o", str(out_abs), "-b", "transparent"],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if out_path.exists() and out_path.stat().st_size > 0:
                return out_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            err = ""
            if isinstance(e, subprocess.CalledProcessError) and e.stderr:
                err = e.stderr[:500]
            logger.warning("mermaid render failed: %s %s", e, err)
    return None
