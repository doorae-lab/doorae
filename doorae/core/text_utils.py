"""Text sanitization helpers for model outputs."""

from __future__ import annotations

import re

_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.DOTALL)
_THINK_TAG_RE = re.compile(r"</?think>")


def strip_thinking_tags(content: str | None) -> str:
    """Remove Qwen-style thinking tags from model output."""
    if not content:
        return ""

    cleaned = _THINK_BLOCK_RE.sub("", content)
    cleaned = _THINK_TAG_RE.sub("", cleaned)
    return cleaned.strip()
