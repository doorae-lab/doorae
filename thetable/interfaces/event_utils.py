"""Shared helpers for interface event parsing."""

from __future__ import annotations

import colorsys
import random
from collections.abc import Mapping, Sequence
from typing import Any


_NON_SPEAKER_NAMES = {"ChatOpenAI", "RunnableSequence"}


def is_delegated(tags: Sequence[str]) -> bool:
    """Return whether an event comes from a delegated turn."""
    return any(tag.startswith("delegated_by:") for tag in tags)


def random_speaker_color() -> str:
    """Generate a readable random hex color for speaker labels."""
    hue = random.random()
    saturation = random.uniform(0.6, 1.0)
    lightness = random.uniform(0.45, 0.65)
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def extract_speaker(event: Mapping[str, Any]) -> str | None:
    """Extract the logical speaker name from a LangGraph event."""
    raw_name = event.get("name")
    if isinstance(raw_name, str) and raw_name and raw_name not in _NON_SPEAKER_NAMES:
        return raw_name

    tags = event.get("tags", [])
    if not isinstance(tags, Sequence):
        return None

    for tag in tags:
        if isinstance(tag, str) and tag.startswith("speaker:"):
            return tag.removeprefix("speaker:")
    return None


def extract_node_name(tags: Sequence[str]) -> str | None:
    """Extract the langgraph node name from tags."""
    try:
        index = tags.index("langgraph_node")
    except ValueError:
        return None

    next_index = index + 1
    if next_index >= len(tags):
        return None
    return tags[next_index]
