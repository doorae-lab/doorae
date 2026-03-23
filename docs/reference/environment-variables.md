# 환경 변수 Reference

소스: `doorae/config/settings.py`, `doorae/server/config.py`, `.env.example`

Doorae는 [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)를 사용한다. `.env` 파일 또는 OS 환경 변수에서 설정을 읽는다. `doorae init` 실행 시 `.env.example` 템플릿이 `.env`로 복사된다.

## Fallback 체인

Main LLM과 Task LLM은 독립된 API 키와 base URL을 가질 수 있다. 전용 값이 `None`이면 공통 fallback으로 대체된다.

```
LLM_MAIN_API_KEY  →  (None이면)  →  OPENAI_API_KEY
LLM_MAIN_BASE_URL →  (None이면)  →  OPENAI_BASE_URL
LLM_TASK_API_KEY  →  (None이면)  →  OPENAI_API_KEY
LLM_TASK_BASE_URL →  (None이면)  →  OPENAI_BASE_URL
```

API 키가 최종적으로 `None`이면 `ValueError`가 발생한다.

## 공통 설정 (Fallback)

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `OPENAI_API_KEY` | `Optional[str]` | `None` | Main/Task 공통 API 키 fallback |
| `OPENAI_BASE_URL` | `Optional[str]` | `None` | 공통 base URL fallback. 기본은 OpenAI 공식 엔드포인트. OpenRouter 사용 시 `https://openrouter.ai/api/v1` |

## Main LLM (회의 에이전트 응답 생성)

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `LLM_MAIN_API_KEY` | `Optional[str]` | `None` | Main LLM 전용 API 키. `None`이면 `OPENAI_API_KEY` 사용 |
| `LLM_MAIN_BASE_URL` | `Optional[str]` | `None` | Main LLM 전용 base URL. `None`이면 `OPENAI_BASE_URL` 사용 |
| `LLM_MAIN_MODEL` | `str` | `"gpt-4o-mini"` | Main LLM 모델명 |
| `LLM_MAIN_TEMPERATURE` | `float` | `0.7` | Main LLM temperature |
| `LLM_MAIN_MAX_TOKENS` | `int` | `4096` | Main LLM 응답 최대 토큰 |

## Task LLM (멘션 추출, 종료 감지, 안건 분석)

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `LLM_TASK_API_KEY` | `Optional[str]` | `None` | Task LLM 전용 API 키. `None`이면 `OPENAI_API_KEY` 사용 |
| `LLM_TASK_BASE_URL` | `Optional[str]` | `None` | Task LLM 전용 base URL. `None`이면 `OPENAI_BASE_URL` 사용 |
| `LLM_TASK_MODEL` | `str` | `"gpt-4o-mini"` | Task LLM 모델명 |
| `LLM_TASK_TEMPERATURE` | `float` | `0.0` | Task LLM temperature. 일관된 결과를 위해 낮게 설정 |
| `LLM_TASK_MAX_TOKENS` | `int` | `256` | Task LLM 응답 최대 토큰 |
| `MENTION_EXTRACTION_MAX_TOKENS` | `int` | `64` | Human fallback 멘션 추출 상한 토큰 |

## LLM 연결 설정

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `LLM_TIMEOUT` | `float` | `60.0` | LLM 요청 타임아웃 (초) |
| `LLM_MAX_RETRIES` | `int` | `3` | LLM 요청 최대 재시도 횟수 |

## LangGraph 설정

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `RECURSION_LIMIT` | `int` | `1000` | LangGraph 재귀 깊이 제한 |
| `MAX_TURNS` | `int` | `1000` | 회의 최대 턴 수 (무한루프 방지) |
| `HOST_CHECKIN_INTERVAL` | `int` | `10` | Host 체크인 주기 (턴 단위). `0`이면 비활성화 |

## 파일 경로

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `AGENT_PROFILES_PATH` | `str` | `"config/agent_profiles.yaml"` | Agent 프로필 YAML 경로 |
| `AGENDAS_PATH` | `str` | `"config/agendas.yaml"` | 안건 YAML 경로 |

## TUI 설정

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `TUI_ENABLED` | `bool` | `True` | TUI 활성화 여부. `--classic` 플래그로 비활성화 가능 |

## 대화 요약 설정

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `MAX_MESSAGES_BEFORE_SUMMARY` | `int` | `8` | 이 개수 초과 시 요약 생성 |
| `KEEP_RECENT_MESSAGES` | `int` | `3` | 요약 후 유지할 최근 메시지 수 |
| `SUMMARY_MAX_TOKENS` | `int` | `3000` | 요약 최대 토큰 |

## LangSmith 추적

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `LANGCHAIN_TRACING_V2` | `bool` | `False` | LangSmith 추적 활성화 |
| `LANGCHAIN_API_KEY` | `Optional[str]` | `None` | LangSmith API 키 |
| `LANGCHAIN_PROJECT` | `str` | `"doorae"` | LangSmith 프로젝트명 |
| `LANGCHAIN_ENDPOINT` | `Optional[str]` | `None` | 커스텀 LangSmith 엔드포인트 |

## 서버 설정

소스: `doorae/server/config.py`

`ServerSettings`는 `env_prefix="SERVER_"` 를 사용하므로, `host`와 `port`는 `SERVER_HOST`, `SERVER_PORT`로 설정한다. 단, `DOORAE_SERVER`는 `validation_alias`를 통해 prefix 없이 직접 읽는다.

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `DOORAE_SERVER` | `Optional[str]` | `None` | 서버 주소 override (`host:port` 형식). 설정 시 `SERVER_HOST`와 `SERVER_PORT`를 덮어쓴다 |
| `SERVER_HOST` | `str` | `"0.0.0.0"` | 서버 바인딩 호스트 |
| `SERVER_PORT` | `int` | `8000` | 서버 바인딩 포트 |
| `SERVER_MAX_ROOMS` | `int` | `100` | 최대 회의방 수 |

## MCP 관련

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|--------|------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `str` | (없음) | GitHub MCP 서버 인증 토큰. `mcp_servers.json`에서 `${GITHUB_PERSONAL_ACCESS_TOKEN}`으로 참조 |
