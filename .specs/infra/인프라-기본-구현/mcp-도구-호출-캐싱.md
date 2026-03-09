# MCP 도구 호출 캐싱

- 상위: [인프라 기본 구현](./__init__.md) - 인프라 핵심 컴포넌트 구현
- 상태: done
- 작성일: 2026-02-26

## 개요

여러 에이전트가 동일한 읽기 전용 MCP 도구를 반복 호출하는 비효율 제거.
`ToolCallInterceptor`를 활용해 `get_`, `list_`, `search_` 접두사 도구 결과를 TTL 120초로 인메모리 캐싱.
모든 에이전트가 동일한 `MultiServerMCPClient`를 공유하므로 캐시가 자동으로 공유된다.

## 설계 결정

- `CACHEABLE_PREFIXES = ("get_", "list_", "search_")`: GitHub MCP REST 네이밍 규칙 기반. write 도구(create_, update_, delete_)는 캐싱 제외
- cache key에 `server_name` 포함: 서버가 다르면 동일한 도구명이라도 키가 구분됨
- TTL 120초: 회의 한 라운드(10~30초) 내 캐시 히트 충분

## 관련 코드

- `doorae/mcp/cache.py`
- `doorae/graph/nodes/utils.py`
- `tests/mcp/test_cache.py`
