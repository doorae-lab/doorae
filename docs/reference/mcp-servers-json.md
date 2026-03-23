# MCP Servers JSON Reference

소스: `doorae/mcp/__init__.py`

`mcp_servers.json` 파일은 MCP (Model Context Protocol) 서버 설정을 정의한다. 에이전트가 외부 도구(GitHub, Jira 등)를 사용할 수 있게 한다.

## JSON 구조

최상위 키는 `mcpServers`이며, 각 서버 이름을 키로 하는 설정 객체를 포함한다.

```json
{
  "mcpServers": {
    "<server-name>": {
      ...server config...
    }
  }
}
```

## 서버 설정 필드

### stdio transport (command 기반)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `command` | `str` | O | 실행할 명령어 |
| `args` | `List[str]` | | 명령어 인자 목록 |
| `env` | `Dict[str, str]` | | 환경 변수 매핑 |
| `transport` | `str` | | 명시하지 않으면 `command` 필드가 있을 때 자동으로 `"stdio"` 추론 |

### streamable_http transport (URL 기반)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `url` | `str` | O | 서버 URL |
| `headers` | `Dict[str, str]` | | HTTP 헤더 (인증 등) |
| `transport` | `str` | | 명시하지 않으면 `url` 필드가 있을 때 자동으로 `"streamable_http"` 추론 |

`streamable_http` transport에서는 `env`와 `args` 필드가 자동으로 제거된다.

## Transport 추론 규칙

`transport` 필드를 명시하지 않으면 다음 규칙으로 추론한다.

1. `transport`가 명시되어 있으면 그대로 사용
2. `url` 필드가 있고 `transport`가 없으면 `"streamable_http"`
3. `command` 필드가 있고 `transport`가 없으면 `"stdio"`

## 환경 변수 치환

모든 문자열 값에서 `${VAR}` 패턴을 `os.environ`의 해당 값으로 치환한다. 환경 변수가 설정되지 않으면 빈 문자열(`""`)로 대체된다.

`.env` 파일은 설정 로드 시 자동으로 읽힌다 (프로젝트 루트 기준).

### streamable_http 인증 검증

`streamable_http` transport에서 `headers`에 `Authorization` 헤더가 있을 때:

- 헤더 값이 비어 있거나 공백만 있으면 제거
- `Authorization` 형식이 `<scheme> <token>`인데 `<token>`이 비어 있으면 제거
- `Authorization` 헤더가 원래 있었지만 필터링으로 제거된 경우, 해당 서버 전체를 건너뛴다 (경고 로그 출력)

## 예시

### stdio transport (GitHub MCP)

```json
{
  "mcpServers": {
    "github": {
      "command": "go",
      "args": [
        "run",
        "github.com/github/github-mcp-server/cmd/github-mcp-server@latest",
        "stdio"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

### streamable_http transport

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://mcp.example.com/api",
      "headers": {
        "Authorization": "Bearer ${MY_SERVICE_TOKEN}"
      }
    }
  }
}
```

### 혼합 설정

```json
{
  "mcpServers": {
    "github": {
      "command": "go",
      "args": ["run", "github.com/github/github-mcp-server/cmd/github-mcp-server@latest", "stdio"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    },
    "jira": {
      "url": "https://mcp-jira.example.com",
      "headers": {
        "Authorization": "Bearer ${JIRA_TOKEN}"
      }
    }
  }
}
```

## Agent에서의 사용

`agent_profiles.yaml`에서 `mcp_tools` 필드에 서버 이름을 지정하면 해당 에이전트가 그 MCP 서버의 도구를 사용할 수 있다.

```yaml
agents:
  - name: PM
    mcp_tools:
      - github
```
