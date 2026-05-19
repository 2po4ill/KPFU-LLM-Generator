"""Normalize Ollama / mock LLM responses to {response, thinking} dict."""

from __future__ import annotations

import re
from typing import Any, Dict


def normalize_llm_response(response: Any) -> Dict[str, str]:
    if isinstance(response, dict):
        return {
            "response": str(response.get("response") or ""),
            "thinking": str(response.get("thinking") or ""),
        }
    resp_text = getattr(response, "response", None)
    think_text = getattr(response, "thinking", None)
    if resp_text is not None or think_text is not None:
        return {
            "response": str(resp_text or ""),
            "thinking": str(think_text or ""),
        }
    return {"response": str(response or ""), "thinking": ""}


def pick_llm_text(response: Any) -> str:
    data = normalize_llm_response(response)
    text = (data.get("response") or "").strip()
    if text:
        return text
    return (data.get("thinking") or "").strip()
