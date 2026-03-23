# 에이전트별 LLM 설정 가이드

각 에이전트마다 다른 LLM 모델, API endpoint, temperature를 지정하여 역할에 맞는 응답 품질과 비용 효율을 달성할 수 있습니다.

---

## 기본 구조

`agent_profiles.yaml`에서 에이전트 정의에 `llm` 필드를 추가합니다.

```yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
    expertise:
      - 일정 계획
    llm:
      model: "gpt-4o"
      api_key: "${PM_API_KEY}"
      base_url: "${PM_BASE_URL}"
      temperature: 0.3
      max_tokens: 4096
```

### llm 필드 스펙

| 필드 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `model` | `string` | LLM 모델 이름 | `LLM_MAIN_MODEL` 설정값 |
| `api_key` | `string` | API 키 (환경변수 치환 가능) | `LLM_MAIN_API_KEY` 또는 `OPENAI_API_KEY` |
| `base_url` | `string` | API endpoint URL | `LLM_MAIN_BASE_URL` 또는 `OPENAI_BASE_URL` |
| `temperature` | `float` | 생성 온도 (0.0 ~ 2.0) | `LLM_MAIN_TEMPERATURE` |
| `max_tokens` | `int` | 최대 응답 토큰 수 | `LLM_MAIN_MAX_TOKENS` |

모든 필드는 선택 사항입니다. 지정하지 않은 필드는 `.env`의 글로벌 Main LLM 설정으로 fallback됩니다.

---

## 환경변수 치환 (${ENV_VAR})

`model`, `api_key`, `base_url` 필드는 `${환경변수명}` 구문으로 런타임에 환경변수 값으로 치환됩니다.

```yaml
llm:
  model: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "${DEEPSEEK_BASE_URL}"
```

치환 규칙:

- `${VAR}` 패턴이 정확히 매치되면 `os.environ.get("VAR")` 값으로 교체
- 환경변수가 설정되지 않으면 `None`이 되어 글로벌 fallback 사용
- 일반 문자열 (환경변수 패턴이 아닌 경우)은 그대로 사용

`.env` 파일에 함께 정의하면 관리가 편합니다:

```env
# .env
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
PM_API_KEY=sk-yyyy
```

---

## Fallback Chain

에이전트별 LLM은 다음 순서로 설정을 resolve합니다:

```
에이전트 llm 필드 → 글로벌 Main LLM 설정 → OPENAI_API_KEY (공통 fallback)
```

구체적으로 각 항목의 resolve 순서:

| 항목 | 1순위 | 2순위 | 3순위 |
|------|-------|-------|-------|
| model | `llm.model` | `LLM_MAIN_MODEL` | `gpt-4o-mini` |
| api_key | `llm.api_key` | `LLM_MAIN_API_KEY` | `OPENAI_API_KEY` |
| base_url | `llm.base_url` | `LLM_MAIN_BASE_URL` | `OPENAI_BASE_URL` |
| temperature | `llm.temperature` | `LLM_MAIN_TEMPERATURE` | `0.7` |
| max_tokens | `llm.max_tokens` | `LLM_MAIN_MAX_TOKENS` | `4096` |

`api_key`가 어떤 레벨에서도 설정되지 않으면 `ValueError`가 발생합니다.

---

## 비용 최적화 패턴

### 패턴 1: 리드에게 고급 모델, 나머지에 경제적 모델

```yaml
agents:
  - name: Host
    role: host
    responsibilities: [...]
    expertise: [...]
    llm:
      model: "gpt-4o"
      temperature: 0.7

  - name: PM
    role: project_manager
    responsibilities: [...]
    expertise: [...]
    # llm 필드 없음 → 글로벌 설정(gpt-4o-mini) 사용

  - name: TechLead
    role: tech_lead
    responsibilities: [...]
    expertise: [...]
    llm:
      model: "gpt-4o"
      temperature: 0.4
    agents:
      - name: Backend
        role: backend_engineer
        responsibilities: [...]
        expertise: [...]
        # sub-agent는 글로벌 설정 사용 (경제적)

      - name: Frontend
        role: frontend_engineer
        responsibilities: [...]
        expertise: [...]
```

이 구성에서 Host, TechLead는 `gpt-4o`를, PM과 sub-agent들은 `.env`의 `LLM_MAIN_MODEL`(기본 `gpt-4o-mini`)을 사용합니다.

### 패턴 2: 다른 프로바이더 혼합

```yaml
agents:
  - name: Host
    role: host
    responsibilities: [...]
    expertise: [...]
    llm:
      model: "deepseek-chat"
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"
      temperature: 0.7

  - name: TechLead
    role: tech_lead
    responsibilities: [...]
    expertise: [...]
    llm:
      model: "claude-sonnet-4-20250514"
      api_key: "${ANTHROPIC_API_KEY}"
      base_url: "https://api.anthropic.com/v1"
      temperature: 0.5
```

OpenAI 호환 API를 제공하는 프로바이더라면 `base_url`만 변경하여 사용할 수 있습니다.

### 패턴 3: 로컬 모델 활용

```yaml
agents:
  - name: Backend
    role: backend_engineer
    responsibilities: [...]
    expertise: [...]
    llm:
      model: "llama3"
      base_url: "http://localhost:11434/v1"
      api_key: "ollama"
      temperature: 0.5
```

Ollama 등 로컬 LLM 서버를 OpenAI 호환 모드로 실행하면 sub-agent에 할당하여 비용을 절감할 수 있습니다.

---

## 설정 확인

`--verbose` 플래그로 실행하면 각 에이전트에 어떤 모델이 할당되었는지 로그에서 확인할 수 있습니다:

```bash
doorae -v -m "설정 테스트"
```

에이전트별 LLM 설정이 `None`으로 resolve되는 필드가 있으면, 해당 필드는 글로벌 설정으로 자동 fallback됩니다.
