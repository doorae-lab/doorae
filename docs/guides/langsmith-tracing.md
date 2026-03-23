# LangSmith 추적 설정 가이드

LangSmith를 통해 Doorae 회의의 LLM 호출, tool 사용, 그래프 실행 흐름을 추적하고 디버깅할 수 있습니다.

---

## 추적 활성화

### 방법 1: CLI 플래그

```bash
doorae --trace -m "회의를 시작합니다"
doorae run --trace --project my-project
```

`--trace` 플래그는 `.env` 설정보다 우선합니다. `--trace`를 명시하지 않으면 `.env`의 `LANGCHAIN_TRACING_V2` 값을 따릅니다.

### 방법 2: 환경변수 (.env)

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxx
LANGCHAIN_PROJECT=doorae
```

---

## 필수 환경변수

| 환경변수 | 설명 | 필수 여부 |
|----------|------|-----------|
| `LANGCHAIN_API_KEY` | LangSmith API 키 | 추적 사용 시 필수 |
| `LANGCHAIN_TRACING_V2` | 추적 활성화 (`true`/`false`) | `--trace` 미사용 시 |
| `LANGCHAIN_PROJECT` | LangSmith 프로젝트 이름 | 선택 (기본: `doorae`) |
| `LANGCHAIN_ENDPOINT` | LangSmith API endpoint | 선택 (기본: LangSmith 공식 endpoint) |

---

## 설정 동작 상세

추적 설정은 `setup_tracing()` 함수에서 처리됩니다:

1. `--trace` 플래그가 있으면 해당 값 사용, 없으면 `LANGCHAIN_TRACING_V2` 환경변수 확인
2. 추적이 비활성화면 `LANGCHAIN_TRACING_V2=false`로 설정 후 종료
3. 추적이 활성화되었는데 `LANGCHAIN_API_KEY`가 없으면 경고 로그 출력 후 추적 비활성화:

```
LangSmith tracing enabled but LANGCHAIN_API_KEY is not set. Tracing will not work.
```

4. API 키가 있으면 환경변수를 설정하고 추적 활성화:

```
LangSmith tracing enabled (project: doorae)
```

---

## 프로젝트별 추적

여러 회의 유형을 LangSmith에서 별도 프로젝트로 분리하려면 `LANGCHAIN_PROJECT`를 변경합니다:

```bash
LANGCHAIN_PROJECT=sprint-review doorae --trace
LANGCHAIN_PROJECT=architecture-review doorae --trace
```

또는 `.env`에서:

```env
LANGCHAIN_PROJECT=my-team-meetings
```

---

## 추적 내용

LangSmith에서 확인할 수 있는 정보:

- **LLM 호출**: 각 에이전트의 프롬프트, 응답, 토큰 사용량
- **Tool 호출**: MCP tool 호출과 응답, sub-agent 위임
- **Graph 실행**: LangGraph 노드 전이 (refill_speakers → participant → process_response)
- **Run 태그**: `participant`, `speaker:{name}`, `delegated_by:{name}` 태그로 에이전트별 필터링

---

## 비용 관련 참고

LangSmith 추적은 LLM API 호출에 추가 오버헤드를 발생시키지 않습니다. LangSmith 자체의 무료 티어는 월 5,000 traces를 제공하며, 일반적인 회의 한 세션은 수십 개의 trace를 생성합니다.

추적이 필요하지 않은 일반 사용에서는 비활성화 상태를 유지하세요:

```env
LANGCHAIN_TRACING_V2=false
```
