"""Tests for interface time formatting helpers."""

from doorae.interfaces.time_utils import format_elapsed


def test_format_elapsed_under_one_hour() -> None:
    assert format_elapsed(0) == "00:00"
    assert format_elapsed(65) == "01:05"
    assert format_elapsed(3599) == "59:59"


def test_format_elapsed_one_hour_or_more() -> None:
    assert format_elapsed(3600) == "01:00:00"
    assert format_elapsed(3661) == "01:01:01"


def test_format_elapsed_negative_clamped_to_zero() -> None:
    assert format_elapsed(-5) == "00:00"
