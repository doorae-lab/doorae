# TheTable 설정 가이드

> 작성일: 2026-02-10
> 버전: 1.0

---

## 목차

- [환경변수 설정 (.env)](#환경변수-설정-env)
- [에이전트 프로필 (agent_profiles.yaml)](#에이전트-프로필-agent_profilesyaml)
- [회의 안건 (agendas.yaml)](#회의-안건-agendasmcpyaml)
- [MCP 서버 설정 (mcp_servers.json)](#mcp-서버-설정-mcp_serversjson)
- [Settings 클래스](#settings-클래스)

---

## 환경변수 설정 (.env)

TheTable은 `.env` 파일을 통해 런타임 환경을 설정합니다.

### 전체 환경변수 목록

#### LLM 설정

**공통 설정 (Fallback)**

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `OPENAI_API_KEY` | Main/Task 공통 fallback API 키 | - | ✅ |
| `OPENAI_BASE_URL` | API base URL | OpenAI 공식 엔드포인트 | ❌ |

**Main LLM (회의 에이전트 응답 생성)**

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LLM_MAIN_API_KEY` | Main LLM 전용 API 키 (None이면 `OPENAI_API_KEY` 사용) | `None` |
| `LLM_MAIN_BASE_URL` | Main LLM 전용 base URL | `None` |
| `LLM_MAIN_MODEL` | Main LLM 모델명 | `gpt-4o-mini` |
| `LLM_MAIN_TEMPERATURE` | Main LLM temperature | `0.7` |
| `LLM_MAIN_MAX_TOKENS` | Main LLM 최대 토큰 | `4096` |

**Task LLM (멘션 추출, 종료 감지, 안건 분석)**

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LLM_TASK_API_KEY` | Task LLM 전용 API 키 (None이면 `OPENAI_API_KEY` 사용) | `None` |
| `LLM_TASK_BASE_URL` | Task LLM 전용 base URL | `None` |
| `LLM_TASK_MODEL` | Task LLM 모델명 | `gpt-4o-mini` |
| `LLM_TASK_TEMPERATURE` | Task LLM temperature | `0.0` |
| `LLM_TASK_MAX_TOKENS` | Task LLM 최대 토큰 | `2048` |

**연결 설정**

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LLM_TIMEOUT` | LLM 호출 타임아웃 (초) | `60.0` |
| `LLM_MAX_RETRIES` | LLM 호출 재시도 횟수 | `3` |

#### LangGraph 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `RECURSION_LIMIT` | LangGraph 재귀 깊이 제한 | `1000` |
| `MAX_TURNS` | 회의 최대 턴 수 (무한루프 방지) | `1000` |

#### 대화 요약 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `MAX_MESSAGES_BEFORE_SUMMARY` | 요약 트리거 메시지 개수 | `5` |
| `KEEP_RECENT_MESSAGES` | 요약 후 유지할 최근 메시지 개수 | `3` |
| `SUMMARY_MAX_TOKENS` | 요약 최대 토큰 수 | `3000` |

#### 파일 경로

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `AGENT_PROFILES_PATH` | 에이전트 프로필 YAML 경로 | `config/agent_profiles.yaml` |
| `AGENDAS_PATH` | 안건 YAML 경로 | `config/agendas.yaml` |

#### MCP Tools

| 변수 | 설명 | 필수 |
|------|------|------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP 서버용 PAT | MCP 사용 시 ✅ |

#### LangSmith Tracing (Optional)

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LANGCHAIN_TRACING_V2` | LangSmith 추적 활성화 | `false` |
| `LANGCHAIN_API_KEY` | LangSmith API 키 | `None` |
| `LANGCHAIN_PROJECT` | LangSmith 프로젝트명 | `thetable` |
| `LANGCHAIN_ENDPOINT` | LangSmith 커스텀 엔드포인트 | `None` |

### 예시 설정

**OpenRouter 사용 (권장)**

```bash
# 공통 설정
OPENAI_API_KEY=your-openrouter-api-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Main LLM (가성비 우수)
LLM_MAIN_MODEL=deepseek/deepseek-v3.2
LLM_MAIN_TEMPERATURE=0.7

# Task LLM (빠른 처리)
LLM_TASK_MODEL=google/gemini-2.5-flash
LLM_TASK_TEMPERATURE=0.0

# MCP
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token
```

**OpenAI 직접 사용**

```bash
# 공통 설정
OPENAI_API_KEY=sk-your-openai-key
# OPENAI_BASE_URL은 생략 (기본값 사용)

# Main LLM
LLM_MAIN_MODEL=gpt-5-mini

# Task LLM
LLM_TASK_MODEL=gpt-5-nano
```

**혼합 provider 사용**

```bash
# Main LLM: OpenRouter
LLM_MAIN_API_KEY=your-openrouter-key
LLM_MAIN_BASE_URL=https://openrouter.ai/api/v1
LLM_MAIN_MODEL=deepseek/deepseek-v3.2

# Task LLM: Azure OpenAI
LLM_TASK_API_KEY=your-azure-key
LLM_TASK_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/gpt-35-turbo
LLM_TASK_MODEL=gpt-35-turbo
```

---

## 에이전트 프로필 (agent_profiles.yaml)

에이전트의 역할, 책임, 전문성, MCP 도구를 정의합니다.

### 스키마

```yaml
agents:
  - name: string              # 에이전트 이름 (필수, 고유해야 함)
    role: string              # 역할 (필수)
    is_human: boolean         # 사람 참여자 여부 (기본값: false)
    responsibilities:         # 책임 목록 (필수)
      - string
      - string
    expertise:                # 전문 분야 (필수)
      - string
      - string
    phase_triggers:           # 단계별 트리거 (선택)
      trigger_key: "trigger message"
    mcp_tools:                # MCP 도구 서버 목록 (선택)
      - server_name
    metadata:                 # 메타데이터 (선택)
      key: value
      additional_instructions: |
        에이전트별 추가 지시사항
    agents:                   # 하위 에이전트 (계층 구조, 선택)
      - name: string
        ...
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | ✅ | 에이전트 이름 (고유해야 함) |
| `role` | string | ✅ | 에이전트 역할 (예: `host`, `project_manager`) |
| `is_human` | boolean | ❌ | 사람 참여자 여부 (기본값: `false`) |
| `responsibilities` | list[string] | ✅ | 에이전트 책임 목록 |
| `expertise` | list[string] | ✅ | 전문 분야 목록 |
| `phase_triggers` | dict | ❌ | 단계별 트리거 메시지 |
| `mcp_tools` | list[string] | ❌ | 사용할 MCP 서버 목록 |
| `metadata` | dict | ❌ | 추가 메타데이터 (도구 사용 컨텍스트) |
| `agents` | list[AgentProfile] | ❌ | 하위 에이전트 (계층 구조) |

### 예시

```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 시작 인사 및 안건 소개
      - 안건 진행 상황 관리
      - 토론 중재 및 의견 요청
      - 회의 요약 및 마무리
    expertise:
      - 회의 퍼실리테이션
      - 시간 관리
    mcp_tools:
      - github
    metadata:
      target_repository: "yaklevel/thetable"
      additional_instructions: |
        GitHub 도구를 적극적으로 사용하여
        프로젝트 상태를 확인하고 발언하세요.

  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 진행 상황 보고
      - 리스크 식별
    expertise:
      - 일정 계획
      - 자원 관리
    phase_triggers:
      status_check: "프로젝트 현황을 보고하세요"
    mcp_tools:
      - github
    metadata:
      target_repository: "yaklevel/thetable"

  # 사람 참여자 예시
  - name: chulsoo
    role: backend_engineer
    is_human: true
    responsibilities:
      - 백엔드 아키텍처 의견 제시
      - 기술적 리스크 검토
    expertise:
      - Python
      - FastAPI
```

### 에이전트 추가 방법

1. `config/agent_profiles.yaml` 파일 편집
2. `agents` 리스트에 새 에이전트 추가
3. 필수 필드 작성: `name`, `role`, `responsibilities`, `expertise`
4. MCP 도구 필요 시 `mcp_tools` 및 `metadata` 추가
5. 저장 후 재실행

---

## 회의 안건 (agendas.yaml)

회의 안건을 정의합니다.

### 스키마

```yaml
agendas:
  - title: string             # 안건 제목 (필수)
    description: string       # 안건 설명 (필수)
    required_speakers:        # 필수 발언자 목록 (선택)
      - agent_name
      - agent_name
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `title` | string | ✅ | 안건 제목 |
| `description` | string | ✅ | 안건 상세 설명 |
| `required_speakers` | list[string] | ❌ | 안건별 필수 발언자 (에이전트 이름) |

### 예시

```yaml
agendas:
  - title: "회의 시작 및 현황 공유"
    description: "회의를 시작하고 주간 현황을 공유합니다"
    required_speakers: ["Host", "PM"]

  - title: "주요 이슈 논의"
    description: "당면한 문제들을 논의하고 해결 방안을 모색합니다"
    required_speakers: ["TechLead"]

  - title: "향후 일정 및 계획"
    description: "다음 단계 일정과 계획을 수립합니다"
    required_speakers: ["PM"]

  - title: "회의 마무리"
    description: "논의 내용을 정리하고 액션 아이템을 확정합니다"
    required_speakers: ["Host"]
```

### 커스텀 안건 작성법

1. `config/agendas.yaml` 파일 편집
2. `agendas` 리스트에 새 안건 추가
3. `title`, `description` 작성
4. `required_speakers`에 해당 안건에서 발언해야 할 에이전트 이름 나열
   - `agent_profiles.yaml`의 `name` 필드와 일치해야 함
5. 저장 후 재실행

**참고**:
- `required_speakers`가 비어있으면 모든 에이전트가 발언 기회를 가짐
- 안건은 순서대로 진행되며, Host 발언에서 완료 키워드 감지 시 다음 안건으로 전환

---

## MCP 서버 설정 (mcp_servers.json)

MCP (Model Context Protocol) 서버 연결 설정을 정의합니다.

### 스키마

```json
{
  "mcpServers": {
    "server_name": {
      "command": "string",           // stdio transport용 실행 명령
      "args": ["string"],            // 명령 인자
      "env": {                       // 환경변수 (${VAR} 형식 치환 지원)
        "KEY": "${ENV_VAR_NAME}"
      },

      // 또는 streamable_http transport
      "url": "https://...",
      "transport": "streamable_http",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    }
  }
}
```

### 필드 설명

**stdio transport**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `command` | string | ✅ | 실행 명령 (예: `go`, `python`) |
| `args` | list[string] | ✅ | 명령 인자 |
| `env` | dict | ❌ | 환경변수 (`${VAR}` 형식으로 `.env` 값 치환) |

**streamable_http transport**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `url` | string | ✅ | MCP 서버 URL |
| `transport` | string | ✅ | `"streamable_http"` |
| `headers` | dict | ❌ | HTTP 헤더 (`${VAR}` 형식 치환 지원) |

### 예시

**GitHub MCP Server (stdio)**

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

**Jira MCP Server (streamable_http)**

```json
{
  "mcpServers": {
    "github": { ... },
    "jira": {
      "url": "https://jira-mcp-server.example.com",
      "transport": "streamable_http",
      "headers": {
        "Authorization": "Bearer ${JIRA_API_TOKEN}"
      }
    }
  }
}
```

### 환경변수 치환

- `${VAR}` 형식의 환경변수는 `.env` 파일의 값으로 치환됨
- 환경변수가 설정되지 않은 경우 해당 서버는 건너뜀 (경고 로그 출력)

### Transport 자동 추론

- `command` 필드가 있으면 **stdio** transport
- `url` 필드가 있으면 **streamable_http** transport

---

## Settings 클래스

TheTable의 중앙 집중식 설정 관리 클래스입니다.

### 위치

`thetable/config/settings.py`

### 특징

- **pydantic-settings 기반**: 환경변수 자동 로드 및 타입 검증
- **lru_cache 싱글턴**: `get_settings()` 호출 시 캐싱된 인스턴스 반환
- **Fallback 메커니즘**: Main/Task LLM 전용 설정이 없으면 공통 설정 사용

### 주요 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `openai_api_key` | Optional[str] | 공통 API 키 (fallback) |
| `openai_base_url` | Optional[str] | 공통 base URL (fallback) |
| `llm_main_model` | str | Main LLM 모델명 |
| `llm_task_model` | str | Task LLM 모델명 |
| `recursion_limit` | int | LangGraph 재귀 제한 |
| `max_turns` | int | 회의 최대 턴 수 |

### Property 메서드

| Property | 반환 타입 | 설명 |
|----------|----------|------|
| `main_api_key` | str | Main LLM API 키 (`llm_main_api_key` 또는 `openai_api_key`) |
| `main_base_url` | Optional[str] | Main LLM base URL (`llm_main_base_url` 또는 `openai_base_url`) |
| `task_api_key` | str | Task LLM API 키 (`llm_task_api_key` 또는 `openai_api_key`) |
| `task_base_url` | Optional[str] | Task LLM base URL (`llm_task_base_url` 또는 `openai_base_url`) |

### 사용 예시

```python
from thetable.config.settings import get_settings

settings = get_settings()

# Main LLM 설정
main_api_key = settings.main_api_key  # fallback 자동 처리
main_model = settings.llm_main_model

# Task LLM 설정
task_api_key = settings.task_api_key
task_model = settings.llm_task_model

# 회의 설정
max_turns = settings.max_turns
```

### Fallback 로직

```python
# Main LLM API 키 결정
main_api_key = settings.llm_main_api_key or settings.openai_api_key
# LLM_MAIN_API_KEY가 None이면 OPENAI_API_KEY 사용

# Task LLM base URL 결정
task_base_url = settings.llm_task_base_url or settings.openai_base_url
# LLM_TASK_BASE_URL이 None이면 OPENAI_BASE_URL 사용
```

### 커스텀 설정 로드

```python
from pathlib import Path
from thetable.config.settings import get_settings

# 커스텀 .env 파일 사용 (캐시 우회)
custom_settings = get_settings(config_path=Path("custom/.env"))
```

---

## 설정 파일 위치 요약

| 파일 | 경로 | 용도 |
|------|------|------|
| `.env` | 프로젝트 루트 | 환경변수 (API 키, 모델 설정) |
| `agent_profiles.yaml` | `config/` | 에이전트 프로필 정의 |
| `agendas.yaml` | `config/` | 회의 안건 정의 |
| `mcp_servers.json` | `config/` | MCP 서버 설정 |
