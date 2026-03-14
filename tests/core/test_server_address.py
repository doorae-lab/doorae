"""Tests for shared server address parsing helpers."""

from __future__ import annotations

import pytest

from doorae.core.server_address import (
    ServerAddressParseError,
    format_host_port,
    parse_server_address,
)


def test_parse_server_address_supports_plain_host_port() -> None:
    parsed = parse_server_address("localhost:8000")

    assert parsed.host == "localhost"
    assert parsed.port == 8000
    assert parsed.netloc == "localhost:8000"


def test_parse_server_address_supports_protocol_input() -> None:
    parsed = parse_server_address("http://127.0.0.1:9000")

    assert parsed.host == "127.0.0.1"
    assert parsed.port == 9000


def test_parse_server_address_rejects_path_suffix() -> None:
    with pytest.raises(ServerAddressParseError, match="invalid_format"):
        parse_server_address("localhost:8000/rooms")


def test_parse_server_address_requires_port() -> None:
    with pytest.raises(ServerAddressParseError, match="missing_port"):
        parse_server_address("localhost")


def test_format_host_port_wraps_ipv6() -> None:
    assert format_host_port("::1", 8000) == "[::1]:8000"
