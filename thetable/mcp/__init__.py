"""MCP server configuration loader and tool management."""

import json
import os
import re
from pathlib import Path
from typing import Any
from loguru import logger

_ENV_VAR_PATTERN = re.compile(r'\$\{(\w+)\}')


def load_mcp_config(
    config_path: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    """JSON에서 MCP 서버 설정을 로드하여 MultiServerMCPClient 형식으로 반환.

    1. .env 파일 로드 (환경변수 설정)
    2. JSON 파일 읽기 (mcpServers 키)
    3. ${VAR} 패턴을 os.environ 값으로 치환
    4. transport 추론: url 있으면 streamable_http, command 있으면 stdio

    Args:
        config_path: JSON 파일 경로. None이면 config/mcp_servers.json 기본 사용.

    Returns:
        MultiServerMCPClient에 전달할 dict.
        예: {"github": {"url": "...", "transport": "streamable_http", "headers": {...}}}
    """
    from dotenv import load_dotenv
    from thetable import PROJECT_ROOT

    # .env 파일 로드 (프로젝트 루트에서)
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "mcp_servers.json"
    else:
        config_path = Path(config_path)

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers", {})
    resolved = _resolve_env_vars(servers)
    return _to_client_config(resolved)


def _resolve_env_vars(obj: Any) -> Any:
    """재귀적으로 ${VAR} 패턴을 환경변수 값으로 치환."""
    if isinstance(obj, str):
        return _ENV_VAR_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), ""), obj
        )
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


def _infer_transport(entry: dict) -> dict:
    """transport 타입 추론

    Args:
        entry: 서버 설정 딕셔너리

    Returns:
        transport가 설정된 딕셔너리
    """
    if "transport" not in entry:
        if "url" in entry:
            entry["transport"] = "streamable_http"
        elif "command" in entry:
            entry["transport"] = "stdio"
    return entry


def _build_streamable_http_headers(name: str, entry: dict) -> dict | None:
    """streamable_http 헤더 필터링 및 검증

    Args:
        name: 서버 이름
        entry: 서버 설정 딕셔너리

    Returns:
        유효한 설정 딕셔너리 또는 None (건너뛰기)
    """
    # 지원되지 않는 파라미터 제거
    entry.pop("env", None)
    entry.pop("args", None)

    if "headers" not in entry:
        return entry

    original_headers = entry["headers"].copy()
    filtered_headers = {}

    for k, v in entry["headers"].items():
        if not v or not v.strip():
            continue

        # Authorization 헤더 특별 처리
        if k == "Authorization":
            parts = v.strip().split(None, 1)
            if len(parts) < 2 or not parts[1]:
                continue

        filtered_headers[k] = v

    entry["headers"] = filtered_headers

    # Authorization 헤더가 필터링되었다면 None 반환 (건너뛰기)
    if "Authorization" in original_headers and "Authorization" not in entry["headers"]:
        logger.warning(f"⚠️  '{name}' MCP 서버 건너뜀: 인증 토큰 환경변수가 설정되지 않음")
        return None

    if not entry["headers"]:
        entry.pop("headers")

    return entry


def _to_client_config(servers: dict) -> dict:
    """mcpServers 포맷 → MultiServerMCPClient 포맷 변환.

    transport 추론 로직:
    - "transport" 명시 → 그대로 사용
    - "url" 있고 transport 없음 → "streamable_http"
    - "command" 있고 transport 없음 → "stdio"

    langchain-mcp-adapters 0.1.0 호환성:
    - streamable_http: env 파라미터 제거 (지원되지 않음)
    - 필수 환경변수 미설정 시 서버 건너뛰기
    """
    result = {}
    for name, cfg in servers.items():
        entry = _infer_transport(dict(cfg))

        # streamable_http 트랜스포트는 특별 처리
        if entry.get("transport") == "streamable_http":
            entry = _build_streamable_http_headers(name, entry)
            if entry is None:  # 건너뛰기
                continue

        result[name] = entry
    return result


async def collect_tools_by_server(
    client,
    server_names: set[str],
) -> dict[str, list]:
    """서버별로 도구를 수집하여 {server_name: [tools]} 딕셔너리 반환.

    각 서버에 대해 client.get_tools(server_name=X)를 1회씩 호출.
    존재하지 않는 서버는 건너뛰고 경고 로그 출력.
    
    Args:
        client: MultiServerMCPClient 인스턴스
        server_names: 로드할 서버 이름 집합
        
    Returns:
        서버 이름을 키로, 도구 리스트를 값으로 하는 딕셔너리
    """
    tools_by_server: dict[str, list] = {}
    for name in server_names:
        try:
            tools_by_server[name] = await client.get_tools(server_name=name)
            logger.info(f"MCP 서버 '{name}': {len(tools_by_server[name])}개 도구 로드")
        except ValueError:
            logger.warning(f"MCP 서버 '{name}'을(를) 찾을 수 없습니다. 건너뜁니다.")
        except Exception as e:
            logger.error(f"MCP 서버 '{name}' 도구 로드 실패: {e}")
    return tools_by_server
