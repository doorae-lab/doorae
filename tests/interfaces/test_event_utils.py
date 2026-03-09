"""Tests for shared interface event helpers."""

import re

from doorae.interfaces.event_utils import (
    extract_node_name,
    extract_speaker,
    is_delegated,
    random_speaker_color,
)


def test_is_delegated_detects_prefix() -> None:
    assert is_delegated(["participant", "delegated_by:Host"]) is True
    assert is_delegated(["participant", "speaker:PM"]) is False


def test_random_speaker_color_returns_hex_color() -> None:
    color = random_speaker_color()

    assert re.fullmatch(r"#[0-9a-f]{6}", color)


def test_extract_speaker_prefers_explicit_name() -> None:
    event = {"name": "PM", "tags": ["participant", "speaker:Fallback"]}

    assert extract_speaker(event) == "PM"


def test_extract_speaker_falls_back_to_speaker_tag() -> None:
    event = {"name": "ChatOpenAI", "tags": ["participant", "speaker:Backend"]}

    assert extract_speaker(event) == "Backend"


def test_extract_speaker_ignores_non_speaker_placeholder_names() -> None:
    event = {"name": "RunnableSequence", "tags": ["participant"]}

    assert extract_speaker(event) is None


def test_extract_node_name_returns_langgraph_target() -> None:
    assert extract_node_name(["langgraph_node", "process_response"]) == "process_response"
    assert extract_node_name(["participant", "speaker:PM"]) is None
