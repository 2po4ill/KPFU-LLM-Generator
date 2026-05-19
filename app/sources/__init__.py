"""Source discovery and direct PDF resolution for RPD."""

from .discovery import build_normalized_sources
from .direct_pdf import download_and_register_direct_pdf

__all__ = ["build_normalized_sources", "download_and_register_direct_pdf"]
