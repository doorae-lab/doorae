"""MCP tool-call result caching interceptor."""
import hashlib
import json
import time
from dataclasses import dataclass, field

from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
)
from loguru import logger

CACHEABLE_PREFIXES = ("get_", "list_", "search_")


@dataclass
class _CacheEntry:
    result: MCPToolCallResult
    created_at: float


@dataclass
class ToolResultCache:
    ttl_seconds: float = 120.0
    _store: dict[str, _CacheEntry] = field(default_factory=dict, repr=False)

    def get(self, key: str) -> MCPToolCallResult | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.created_at > self.ttl_seconds:
            del self._store[key]
            return None
        return entry.result

    def set(self, key: str, result: MCPToolCallResult) -> None:
        self._store[key] = _CacheEntry(result=result, created_at=time.monotonic())

    def clear(self) -> None:
        self._store.clear()


def _make_cache_key(request: MCPToolCallRequest) -> str:
    raw = json.dumps(
        {"server": request.server_name, "name": request.name, "args": request.args},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _is_cacheable(tool_name: str) -> bool:
    return tool_name.startswith(CACHEABLE_PREFIXES)


class CachingInterceptor:
    """읽기 전용 MCP 도구 결과를 캐싱하는 인터셉터."""

    def __init__(self, cache: ToolResultCache | None = None) -> None:
        self._cache = cache or ToolResultCache()

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler,
    ) -> MCPToolCallResult:
        if not _is_cacheable(request.name):
            return await handler(request)
        key = _make_cache_key(request)
        cached = self._cache.get(key)
        if cached is not None:
            logger.info(f"[cache] HIT: {request.name}")
            return cached
        logger.debug(f"[cache] MISS: {request.name}")
        result = await handler(request)
        self._cache.set(key, result)
        return result
