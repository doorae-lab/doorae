# LLM Provider 설정

이 튜토리얼에서는 다양한 LLM provider(OpenAI, OpenRouter, Azure OpenAI, Ollama)를 설정하는 방법과 에이전트별 LLM override를 구성하는 방법을 안내합니다.

## 사전 준비

- Doorae 클론 및 의존성 설치 완료
- 사용할 LLM provider의 API key 발급 완료

## Doorae의 LLM 구조 이해하기

Doorae는 두 종류의 LLM을 사용합니다:

| LLM 유형 | 용도 | 기본 모델 |
|----------|------|-----------|
| **Main LLM** | 회의 에이전트의 응답 생성 | `gpt-4o-mini` |
| **Task LLM** | 멘션 추출, 종료 감지, 안건 분석 등 보조 작업 | `gpt-4o-mini` |

Main LLM과 Task LLM은 각각 다른 provider와 모델을 사용할 수 있습니다. 설정하지 않으면 공통 설정(`OPENAI_API_KEY`, `OPENAI_BASE_URL`)을 fallback으로 사용합니다.

**설정 우선순위:**

1. 에이전트별 `llm` 설정 (가장 높음)
2. Main/Task 전용 설정 (`LLM_MAIN_*`, `LLM_TASK_*`)
3. 공통 설정 (`OPENAI_API_KEY`, `OPENAI_BASE_URL`)

## 방법 1: OpenRouter (권장)

OpenRouter는 다양한 모델을 단일 API로 사용할 수 있어 가성비가 좋습니다.

`.env` 파일:

```env
# 공통 설정
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Main LLM (회의 에이전트 응답)
LLM_MAIN_MODEL=qwen/qwen3.5-flash-02-23
LLM_MAIN_TEMPERATURE=0.7
LLM_MAIN_MAX_TOKENS=4096

# Task LLM (보조 작업)
LLM_TASK_MODEL=google/gemini-2.5-flash
LLM_TASK_TEMPERATURE=0.0
LLM_TASK_MAX_TOKENS=256
```

설정 후 확인:

```bash
uv run doorae run --project <프로젝트명>
```

## 방법 2: OpenAI 직접 사용

OpenAI API를 직접 사용하는 경우:

`.env` 파일:

```env
# 공통 설정
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Main LLM
LLM_MAIN_MODEL=gpt-5-mini
LLM_MAIN_TEMPERATURE=0.7
LLM_MAIN_MAX_TOKENS=4096

# Task LLM
LLM_TASK_MODEL=gpt-5-nano
LLM_TASK_TEMPERATURE=0.0
LLM_TASK_MAX_TOKENS=256
```

## 방법 3: Azure OpenAI

Azure OpenAI를 사용하는 경우, Main과 Task를 각각 별도의 deployment로 설정합니다:

`.env` 파일:

```env
# Main LLM (Azure deployment)
LLM_MAIN_API_KEY=your-azure-api-key
LLM_MAIN_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/gpt-4o-mini
LLM_MAIN_MODEL=gpt-4o-mini
LLM_MAIN_TEMPERATURE=0.7
LLM_MAIN_MAX_TOKENS=4096

# Task LLM (Azure deployment)
LLM_TASK_API_KEY=your-azure-api-key
LLM_TASK_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/gpt-35-turbo
LLM_TASK_MODEL=gpt-35-turbo
LLM_TASK_TEMPERATURE=0.0
LLM_TASK_MAX_TOKENS=256
```

Azure OpenAI는 deployment별로 `BASE_URL`이 다르므로, Main과 Task 전용 설정(`LLM_MAIN_*`, `LLM_TASK_*`)을 사용합니다.

## 방법 4: 로컬 Ollama

Ollama로 로컬 모델을 사용하는 경우:

먼저 Ollama를 설치하고 모델을 다운로드합니다:

```bash
ollama pull llama3
ollama serve
```

`.env` 파일:

```env
# 공통 설정 (Ollama는 API key 불필요, 더미 값 사용)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1

# Main LLM
LLM_MAIN_MODEL=llama3
LLM_MAIN_TEMPERATURE=0.7
LLM_MAIN_MAX_TOKENS=4096

# Task LLM (같은 모델 또는 다른 로컬 모델)
LLM_TASK_MODEL=llama3
LLM_TASK_TEMPERATURE=0.0
LLM_TASK_MAX_TOKENS=256
```

Ollama는 OpenAI 호환 API(`/v1`)를 제공하므로 별도 설정 없이 사용 가능합니다.

## 에이전트별 LLM Override

특정 에이전트만 다른 모델이나 provider를 사용하도록 설정할 수 있습니다. `config/agent_profiles.yaml`에서 해당 에이전트의 `llm` 필드를 추가합니다:

```yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 이슈 상태 관리
    expertise:
      - 일정 계획
    llm:
      model: "gpt-4.1-mini"
      api_key: "${OPENROUTER_API_KEY}"
      base_url: "https://openrouter.ai/api/v1"
      temperature: 0.2
      max_tokens: 3000

  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
    expertise:
      - 시스템 설계
    # llm 미설정 → 글로벌 .env의 Main LLM 설정 사용
```

**`llm` 필드 구조:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `model` | `str` | 사용할 모델 이름 |
| `api_key` | `str` | API key (`${ENV_VAR}` 문법 지원) |
| `base_url` | `str` | API base URL (`${ENV_VAR}` 문법 지원) |
| `temperature` | `float` | 응답 온도 (0.0~2.0) |
| `max_tokens` | `int` | 응답 최대 토큰 수 |

**`${ENV_VAR}` 문법:** `api_key`와 `base_url`, `model`에서 `${변수명}` 형식을 사용하면 `.env` 파일의 환경 변수 값으로 자동 치환됩니다. 해당 환경 변수가 설정되지 않으면 `None`이 됩니다.

### 활용 예시: Main은 OpenRouter, PM만 OpenAI 직접 사용

`.env`:

```env
OPENAI_API_KEY=sk-or-v1-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MAIN_MODEL=qwen/qwen3.5-flash-02-23

# PM 전용 OpenAI key
PM_OPENAI_KEY=sk-openai-direct-key
```

`config/agent_profiles.yaml`:

```yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
    expertise:
      - 일정 계획
    llm:
      model: "gpt-5-mini"
      api_key: "${PM_OPENAI_KEY}"
      base_url: "https://api.openai.com/v1"

  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
    expertise:
      - 시스템 설계
    # 글로벌 설정(OpenRouter) 사용
```

## 공통 연결 설정

모든 provider에 공통으로 적용되는 연결 설정입니다:

```env
LLM_TIMEOUT=60.0      # API 요청 타임아웃 (초)
LLM_MAX_RETRIES=3     # 실패 시 재시도 횟수
```

## 전체 환경 변수 목록

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | 공통 API key (fallback) | -- |
| `OPENAI_BASE_URL` | 공통 base URL (fallback) | -- |
| `LLM_MAIN_API_KEY` | Main LLM 전용 API key | `OPENAI_API_KEY` |
| `LLM_MAIN_BASE_URL` | Main LLM 전용 base URL | `OPENAI_BASE_URL` |
| `LLM_MAIN_MODEL` | Main LLM 모델 | `gpt-4o-mini` |
| `LLM_MAIN_TEMPERATURE` | Main LLM 온도 | `0.7` |
| `LLM_MAIN_MAX_TOKENS` | Main LLM 최대 토큰 | `4096` |
| `LLM_TASK_API_KEY` | Task LLM 전용 API key | `OPENAI_API_KEY` |
| `LLM_TASK_BASE_URL` | Task LLM 전용 base URL | `OPENAI_BASE_URL` |
| `LLM_TASK_MODEL` | Task LLM 모델 | `gpt-4o-mini` |
| `LLM_TASK_TEMPERATURE` | Task LLM 온도 | `0.0` |
| `LLM_TASK_MAX_TOKENS` | Task LLM 최대 토큰 | `256` |
| `MENTION_EXTRACTION_MAX_TOKENS` | 멘션 추출 토큰 상한 | `64` |
| `LLM_TIMEOUT` | API 타임아웃 (초) | `60.0` |
| `LLM_MAX_RETRIES` | 재시도 횟수 | `3` |

## 다음 단계

- [프로젝트 워크스페이스](project-workspace.md) - 워크스페이스와 프로젝트 구성하기
- [커스텀 에이전트 프로필](custom-agent-profiles.md) - 에이전트 정의 및 LLM override 적용하기
