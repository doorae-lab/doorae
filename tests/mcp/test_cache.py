"""Unit tests for MCP tool-call result caching interceptor."""
import time
import pytest
from unittest.mock import AsyncMock

from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import CallToolResult, TextContent

from thetable.mcp.cache import (
    CachingInterceptor,
    ToolResultCache,
    _is_cacheable,
    _make_cache_key,
)


def _make_request(name: str, args: dict | None = None) -> MCPToolCallRequest:
    return MCPToolCallRequest(name=name, args=args or {}, server_name="test")


def _make_result(content: str = "ok") -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=content)])


# --- _is_cacheable ---

@pytest.mark.parametrize("name", ["get_issue", "list_repos", "search_code"])
def test_is_cacheable_true(name):
    assert _is_cacheable(name) is True


@pytest.mark.parametrize("name", ["create_issue", "update_label", "add_comment", "delete_branch"])
def test_is_cacheable_false(name):
    assert _is_cacheable(name) is False


# --- _make_cache_key ---

def test_make_cache_key_deterministic():
    req = _make_request("get_issue", {"number": 42})
    assert _make_cache_key(req) == _make_cache_key(req)


def test_make_cache_key_different_args():
    req1 = _make_request("get_issue", {"number": 42})
    req2 = _make_request("get_issue", {"number": 99})
    assert _make_cache_key(req1) != _make_cache_key(req2)


def test_make_cache_key_arg_order_independent():
    req1 = _make_request("get_issue", {"a": 1, "b": 2})
    req2 = _make_request("get_issue", {"b": 2, "a": 1})
    assert _make_cache_key(req1) == _make_cache_key(req2)


def test_make_cache_key_different_servers():
    req1 = MCPToolCallRequest(name="get_issue", args={"number": 1}, server_name="github")
    req2 = MCPToolCallRequest(name="get_issue", args={"number": 1}, server_name="gitlab")
    assert _make_cache_key(req1) != _make_cache_key(req2)


# --- ToolResultCache ---

def test_cache_set_and_get():
    cache = ToolResultCache()
    result = _make_result("data")
    cache.set("key1", result)
    assert cache.get("key1") is result


def test_cache_miss_returns_none():
    cache = ToolResultCache()
    assert cache.get("nonexistent") is None


def test_cache_ttl_expiry(monkeypatch):
    cache = ToolResultCache(ttl_seconds=1.0)
    result = _make_result("data")
    cache.set("key1", result)

    # Simulate TTL expiry
    original_monotonic = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original_monotonic() + 2.0)

    assert cache.get("key1") is None


def test_cache_clear():
    cache = ToolResultCache()
    cache.set("key1", _make_result("a"))
    cache.set("key2", _make_result("b"))
    cache.clear()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


# --- CachingInterceptor ---

@pytest.mark.asyncio
async def test_cache_hit_skips_handler():
    interceptor = CachingInterceptor()
    request = _make_request("get_issue", {"number": 42})
    result = _make_result("issue data")

    handler = AsyncMock(return_value=result)

    # First call: MISS → handler called
    first = await interceptor(request, handler)
    assert handler.call_count == 1
    assert first is result

    # Second call: HIT → handler not called
    second = await interceptor(request, handler)
    assert handler.call_count == 1  # still 1
    assert second is result


@pytest.mark.asyncio
async def test_write_tool_always_calls_handler():
    interceptor = CachingInterceptor()
    request = _make_request("create_issue", {"title": "bug"})
    result = _make_result("created")

    handler = AsyncMock(return_value=result)

    await interceptor(request, handler)
    await interceptor(request, handler)

    assert handler.call_count == 2  # called every time, no caching


@pytest.mark.asyncio
async def test_shared_cache_between_interceptors():
    shared = ToolResultCache()
    interceptor_a = CachingInterceptor(cache=shared)
    interceptor_b = CachingInterceptor(cache=shared)

    request = _make_request("list_repos", {"org": "example"})
    result = _make_result("repos")
    handler = AsyncMock(return_value=result)

    # interceptor_b reuses cache populated by interceptor_a
    await interceptor_a(request, handler)
    await interceptor_b(request, handler)

    assert handler.call_count == 1
