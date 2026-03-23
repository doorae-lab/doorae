# 계층적 위임 구조 가이드

Doorae는 supervisor/sub-agent 패턴을 지원하여, 상위 에이전트가 하위 에이전트에게 전문 영역의 작업을 위임할 수 있습니다.

---

## 기본 개념

`agent_profiles.yaml`에서 에이전트 정의 안에 `agents` 필드를 추가하면, 해당 에이전트가 supervisor가 되고 내부의 에이전트들이 sub-agent가 됩니다.

```yaml
agents:
  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
      - 아키텍처 설계
    expertise:
      - 시스템 설계
    agents:                      # ← sub-agents
      - name: Backend
        role: backend_engineer
        responsibilities:
          - API 설계 및 구현
          - 데이터베이스 최적화
        expertise:
          - Python
          - FastAPI
      - name: Frontend
        role: frontend_engineer
        responsibilities:
          - UI 컴포넌트 구현
          - 사용자 경험 최적화
        expertise:
          - React
          - TypeScript
```

### 핵심 규칙

- supervisor(`is_supervisor() == True`)는 `agents` 목록을 가진 에이전트
- sub-agent는 회의의 최상위 참여자로 직접 발언하지 않음
- sub-agent는 오직 supervisor의 tool 호출을 통해서만 응답
- 계층은 재귀적 — sub-agent도 자체 `agents`를 가질 수 있음
- 순환 참조는 자동 감지되어 `ValueError` 발생

---

## ask_{agent} Tool 동작 원리

supervisor가 생성될 때, 각 sub-agent에 대해 `ask_{agent_name}` tool이 자동으로 생성됩니다.

### Tool 생성 규칙

에이전트 이름은 정규화되어 tool 이름에 사용됩니다:

| 에이전트 이름 | 생성되는 tool 이름 |
|--------------|-------------------|
| `Backend` | `ask_backend` |
| `Frontend` | `ask_frontend` |
| `DevOps-Engineer` | `ask_devops_engineer` |

정규화 규칙: 소문자로 변환 후 영숫자와 `_`를 제외한 문자를 `_`로 치환.

### Tool 설명 자동 생성

tool 설명은 sub-agent의 프로필 정보에서 자동 생성됩니다:

```
Backend(backend_engineer)에게 의견을 요청합니다.
상위 에이전트: TechLead.
책임: API 설계 및 구현, 데이터베이스 최적화, 서버 로직 개발.
전문분야: Python, PostgreSQL, FastAPI.
```

LLM은 이 설명을 보고 적절한 sub-agent에게 위임 여부를 판단합니다.

### Tool 입력 스키마

```json
{
  "question": "하위 에이전트에게 전달할 질문/요청"
}
```

supervisor가 tool을 호출하면:

1. sub-agent용 LLM이 초기화됨 (sub-agent에 `llm` 필드가 있으면 해당 설정 사용)
2. sub-agent의 프로필 정보와 질문이 system/human message로 구성됨
3. sub-agent가 MCP tool을 가지고 있으면 (`mcp_tools` 필드), 해당 tool도 바인딩됨
4. 응답이 supervisor에게 반환됨

---

## Supervisor Prompt 구조

supervisor에게는 자동으로 handoff tool 안내가 포함된 프롬프트가 생성됩니다:

```
You are TechLead, a tech_lead managing: Backend, Frontend.

## Available Handoff Tools (IMPORTANT!)
- ask_backend: Backend에게 작업 위임
- ask_frontend: Frontend에게 작업 위임

## Your Responsibilities
- 기술 의사결정
- 아키텍처 설계

## CRITICAL RULES
1. To delegate a task, you MUST call the corresponding transfer tool
2. If you only output text without calling a tool, the delegation will fail
3. Always call a transfer tool after explaining your decision

Delegate tasks to the appropriate team member based on their expertise.
Respond in Korean.
```

---

## 설정 예제: 3단계 계층

```yaml
agents:
  - name: CTO
    role: chief_technology_officer
    responsibilities:
      - 기술 전략 수립
      - 팀 간 조율
    expertise:
      - 기술 전략
    agents:
      - name: TechLead
        role: tech_lead
        responsibilities:
          - 기술 의사결정
        expertise:
          - 시스템 설계
        agents:
          - name: Backend
            role: backend_engineer
            responsibilities:
              - API 구현
            expertise:
              - Python

      - name: DesignLead
        role: design_lead
        responsibilities:
          - 디자인 시스템 관리
        expertise:
          - UI/UX
        agents:
          - name: Frontend
            role: frontend_engineer
            responsibilities:
              - UI 구현
            expertise:
              - React
```

이 구성에서:

- CTO는 `ask_techlead`, `ask_designlead` tool을 가짐
- TechLead는 `ask_backend` tool을 가짐
- DesignLead는 `ask_frontend` tool을 가짐
- Backend, Frontend는 tool이 없는 leaf 에이전트

---

## Sub-agent에 MCP Tool 할당

sub-agent도 `mcp_tools` 필드를 통해 외부 tool을 사용할 수 있습니다:

```yaml
agents:
  - name: TechLead
    role: tech_lead
    responsibilities: [...]
    expertise: [...]
    mcp_tools:
      - github
    agents:
      - name: Backend
        role: backend_engineer
        responsibilities: [...]
        expertise: [...]
        mcp_tools:
          - github          # ← sub-agent도 github tool 사용 가능
```

supervisor가 `ask_backend`를 호출하면, Backend 에이전트는 github MCP tool이 바인딩된 상태로 응답합니다.

---

## 위임 발언 표시 제어

### TUI 모드

`Ctrl+D`를 누르면 위임된 발언의 표시/숨김을 토글합니다. 위임 발언은 들여쓰기되고 반투명 스타일로 표시됩니다.

### Classic CLI 모드

`--hide-delegated` 플래그로 위임 발언을 숨깁니다:

```bash
doorae --classic --hide-delegated
```

---

## 순환 참조 방지

에이전트 프로필 로딩 시 순환 참조가 자동 감지됩니다:

```yaml
# 이 설정은 에러 발생
agents:
  - name: A
    agents:
      - name: B
        agents:
          - name: A    # ← 순환 참조!
```

```
ValueError: Agent cycle detected: A -> B -> A
```

### 중복 이름 감지

모든 레벨에서 에이전트 이름은 고유해야 합니다:

```
ValueError: Duplicate agent name detected: Backend
```

---

## is_human 에이전트와의 조합

`is_human: true` 에이전트에는 `agents` 필드가 무시됩니다. 경고 로그가 출력됩니다:

```
[chulsoo] is_human=true 이므로 agents 필드는 무시됩니다.
```

사용자 참여자는 항상 최상위 레벨에 배치하세요:

```yaml
agents:
  - name: TechLead
    role: tech_lead
    agents:
      - name: Backend
        role: backend_engineer

  - name: chulsoo
    role: backend_engineer
    is_human: true
    responsibilities:
      - 백엔드 의견 제시
    expertise:
      - Python
```
