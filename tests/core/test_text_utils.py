"""Tests for text sanitization helpers."""

from doorae.core.text_utils import strip_thinking_tags


def test_strip_empty_string():
    assert strip_thinking_tags("") == ""


def test_strip_none_returns_empty_string():
    assert strip_thinking_tags(None) == ""


def test_strip_no_tags():
    assert strip_thinking_tags("hello") == "hello"


def test_strip_think_block():
    assert strip_thinking_tags("<think>reasoning</think>real") == "real"


def test_strip_think_only():
    assert strip_thinking_tags("<think>reasoning</think>") == ""


def test_strip_closing_tag_only():
    assert strip_thinking_tags("</think>\ncontent") == "content"


def test_strip_multiline_think():
    assert (
        strip_thinking_tags("<think>\nline1\nline2\n</think>\nok")
        == "ok"
    )
