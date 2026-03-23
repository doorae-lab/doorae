# 비용 최적화 가이드

Doorae는 LLM API 호출이 비용의 대부분을 차지합니다. Dual LLM 전략, 에이전트별 모델 배정, MCP 캐싱, 요약 설정을 조합하여 품질을 유지하면서 비용을 절감할 수 있습니다.

---

## Dual LLM 전략

Doorae는 두 종류의 LLM을 사용합니다:

| LLM | 역할 | 호출 빈도 | 필요 품질 |
|-----|------|-----------|-----------|
| **Main LLM** | 에이전트 대화 응답 생성, 발언자 선정 | 매 턴마다 | 높음 |
| **Task LLM** | 멘션 추출, 안건 상태 분석, 종료 감지 | 매 턴 후처리 | 낮음 |

### 환경변수 설정

```env
# Main LLM — 회의 대화 품질을 결정
LLM_MAIN_MODEL=gpt-4o-mini
LLM_MAIN_API_KEY=sk-xxxx
LLM_MAIN_BASE_URL=              # 비워두면 OpenAI 공식 endpoint
LLM_MAIN_TEMPERATURE=0.7
LLM_MAIN_MAX_TOKENS=4096

# Task LLM — 내부 분석용, 저비용 모델로 충분
LLM_TASK_MODEL=gpt-4o-mini
LLM_TASK_API_KEY=sk-xxxx
LLM_TASK_BASE_URL=
LLM_TASK_TEMPERATURE=0.0        # 일관된 결과를 위해 낮게
LLM_TASK_MAX_TOKENS=256         # 짧은 응답만 필요

# 공통 fallback
OPENAI_API_KEY=sk-xxxx          # Main/Task API key 미설정 시 사용
OPENAI_BASE_URL=                # Main/Task base_url 미설정 시 사용
```

### Fallback 구조

API 키 resolve 순서:

```
LLM_MAIN_API_KEY → OPENAI_API_KEY
LLM_TASK_API_KEY → OPENAI_API_KEY
```

하나의 `OPENAI_API_KEY`만 설정해도 Main과 Task 모두 동작합니다. 다른 프로바이더를 사용하려면 각각의 전용 키를 설정하세요.

---

## 추천 모델 조합

### 균형형 (품질 우선)

```env
LLM_MAIN_MODEL=gpt-4o
LLM_TASK_MODEL=gpt-4o-mini
```

Main에 고급 모델, Task에 경제적 모델. 대화 품질이 중요한 의사결정 회의에 적합합니다.

### 경제형 (비용 우선)

```env
LLM_MAIN_MODEL=gpt-4o-mini
LLM_TASK_MODEL=gpt-4o-mini
```

기본 설정. 일상적인 스탠드업이나 진행 확인 회의에 적합합니다.

### 하이브리드 (다른 프로바이더 혼합)

```env
# Main — 대화용 (DeepSeek)
LLM_MAIN_MODEL=deepseek-chat
LLM_MAIN_API_KEY=sk-deepseek-xxxx
LLM_MAIN_BASE_URL=https://api.deepseek.com/v1

# Task — 분석용 (Google)
LLM_TASK_MODEL=gemini-2.5-flash
LLM_TASK_API_KEY=google-api-key
LLM_TASK_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
```

OpenAI 호환 API를 제공하는 프로바이더끼리 자유롭게 조합할 수 있습니다.

### 에이전트별 차등 배정

Main/Task 설정 위에 `agent_profiles.yaml`의 `llm` 필드를 추가하면 에이전트별로 모델을 다르게 지정할 수 있습니다:

```yaml
agents:
  - name: Host
    role: host
    llm:
      model: "gpt-4o"           # 진행자는 고급 모델
      temperature: 0.7

  - name: PM
    role: project_manager
    # llm 없음 → Main LLM 사용 (gpt-4o-mini)

  - name: TechLead
    role: tech_lead
    llm:
      model: "gpt-4o"           # 기술 리더도 고급 모델
    agents:
      - name: Backend
        role: backend_engineer
        # sub-agent는 Main LLM 사용 (경제적)
      - name: Frontend
        role: frontend_engineer
```

자세한 설정 방법은 [에이전트별 LLM 설정 가이드](per-agent-llm.md)를 참고하세요.

---

## MCP Tool 캐싱

MCP tool 호출 결과는 자동으로 캐싱되어 동일한 요청의 반복 API 호출을 방지합니다.

### 캐싱 대상

`get_`, `list_`, `search_` 접두사로 시작하는 읽기 전용 tool만 캐싱됩니다:

| 캐싱 O | 캐싱 X |
|--------|--------|
| `get_issue` | `create_issue` |
| `list_pull_requests` | `update_issue` |
| `search_code` | `merge_pull_request` |

### 캐시 동작

- TTL: 120초 (2분)
- 캐시 키: 서버 이름 + tool 이름 + 인자의 SHA-256 해시
- 캐시 hit 시 `[cache] HIT: get_issue` 로그 출력 (verbose 모드)
- TTL 만료 시 자동 제거

### 비용 절감 효과

같은 안건을 논의하는 동안 여러 에이전트가 동일한 GitHub issue를 조회하면, 첫 번째 호출만 실제 API를 사용하고 나머지는 캐시에서 반환됩니다.

---

## 요약 설정 튜닝

대화가 길어지면 자동 요약이 실행됩니다. 요약 빈도와 품질을 조정하여 비용을 관리할 수 있습니다.

### 관련 설정

```env
MAX_MESSAGES_BEFORE_SUMMARY=8    # 이 개수 초과 시 요약 실행
KEEP_RECENT_MESSAGES=3           # 요약 후 유지할 최근 메시지 수
SUMMARY_MAX_TOKENS=3000          # 요약 최대 토큰 수
```

### 비용에 미치는 영향

| 설정 변경 | 비용 효과 | 품질 영향 |
|-----------|-----------|-----------|
| `MAX_MESSAGES_BEFORE_SUMMARY` 낮춤 | 요약 LLM 호출 증가, 하지만 이후 대화 context 축소 | 맥락 손실 가능 |
| `MAX_MESSAGES_BEFORE_SUMMARY` 높임 | 요약 빈도 감소, 하지만 긴 context 전달 | 에이전트 응답에 더 많은 맥락 |
| `KEEP_RECENT_MESSAGES` 낮춤 | 매 턴 전달 토큰 감소 | 최근 맥락 부족 |
| `SUMMARY_MAX_TOKENS` 낮춤 | 요약이 짧아짐 | 요약 품질 저하 |

### 추천 설정

짧은 회의 (안건 2-3개):

```env
MAX_MESSAGES_BEFORE_SUMMARY=12
KEEP_RECENT_MESSAGES=5
```

긴 회의 (안건 5개 이상):

```env
MAX_MESSAGES_BEFORE_SUMMARY=6
KEEP_RECENT_MESSAGES=3
SUMMARY_MAX_TOKENS=2000
```

---

## 추가 비용 절감 팁

### 1. max_turns 제한

무한루프 방지 설정을 활용하세요:

```env
MAX_TURNS=100    # 회의 최대 턴 수 (기본: 1000)
```

### 2. 멘션 추출 토큰 제한

```env
MENTION_EXTRACTION_MAX_TOKENS=64    # 멘션 추출 응답 상한
```

### 3. Host 체크인 주기

```env
HOST_CHECKIN_INTERVAL=10    # 0이면 비활성화
```

Host 체크인을 비활성화하면 Host의 중간 발언이 줄어 전체 토큰 사용량이 감소합니다. 다만 회의 진행 품질에 영향을 줄 수 있습니다.

### 4. recursion_limit

```env
RECURSION_LIMIT=500    # 기본: 1000
```

LangGraph 재귀 깊이를 줄이면 비정상적으로 긴 회의 세션을 조기 차단합니다.
