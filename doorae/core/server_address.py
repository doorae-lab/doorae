"""Shared host:port parsing helpers for CLI and server config."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class ParsedServerAddress:
    host: str
    port: int

    @property
    def netloc(self) -> str:
        return format_host_port(self.host, self.port)


class ServerAddressParseError(ValueError):
    """Raised when a server address cannot be parsed as host:port."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def format_host_port(host: str, port: int) -> str:
    rendered_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"{rendered_host}:{port}"


def parse_server_address(server_address: str) -> ParsedServerAddress:
    normalized = server_address.strip()
    if not normalized:
        raise ServerAddressParseError("empty")

    candidate = normalized if "://" in normalized else f"http://{normalized}"
    parsed = urlsplit(candidate)
    if not parsed.hostname:
        raise ServerAddressParseError("missing_host")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ServerAddressParseError("invalid_format")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ServerAddressParseError("invalid_port") from exc
    if port is None:
        raise ServerAddressParseError("missing_port")

    return ParsedServerAddress(host=parsed.hostname, port=port)
