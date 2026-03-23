# 커스텀 에이전트 프로필

이 튜토리얼에서는 `agent_profiles.yaml`에 새로운 에이전트(Designer)를 추가하고, 회의에서 해당 에이전트가 참여하는 것을 확인합니다.

## 사전 준비

- [프로젝트 워크스페이스](project-workspace.md) 튜토리얼을 완료했거나, `doorae init` + `doorae project create`를 실행한 상태
- `.env`에 API key가 설정된 상태

## 1단계: 기본 프로필 구조 이해하기

`agent_profiles.yaml`의 각 에이전트는 다음 필드로 정의됩니다:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | `str` | O | 에이전트 이름 (회의에서 `@Name`으로 호출) |
| `role` | `str` | O | 역할 식별자 (예: `designer`, `backend_engineer`) |
| `responsibilities` | `list[str]` | O | 담당 업무 목록 |
| `expertise` | `list[str]` | O | 전문 분야 목록 |
| `phase_triggers` | `dict[str, str]` | X | 특정 phase에서 자동 발언 트리거 |
| `mcp_tools` | `list[str]` | X | 사용할 MCP 서버 목록 (예: `["github"]`) |
| `metadata` | `dict` | X | 추가 메타데이터 (예: `target_repository`) |
| `llm` | `AgentLLMConfig` | X | 에이전트별 LLM 설정 override |
| `is_human` | `bool` | X | `true`이면 사람 참여자 (기본값: `false`) |
| `agents` | `list[AgentProfile]` | X | 하위 에이전트 목록 (계층 구조) |

## 2단계: Designer 에이전트 추가하기

프로젝트의 `config/agent_profiles.yaml` 파일을 엽니다. 기본 scaffold를 사용했다면 `.doorae/projects/<프로젝트명>/config/agent_profiles.yaml` 경로에 있습니다.

기존 에이전트 목록 끝에 Designer를 추가합니다:

```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 시작 인사 및 안건 소개
      - 안건 진행 상황 관리
      - 토론 중재 및 의견 요청
      - 안건 완료 시 다음 안건으로 전환 안내
      - 회의 요약 및 마무리
    expertise:
      - 회의 퍼실리테이션
      - 시간 관리
    phase_triggers: {}

  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 이슈 상태 관리
      - 진행 상황 보고
    expertise:
      - 일정 계획
      - 자원 관리

  - name: Designer
    role: designer
    responsibilities:
      - UI/UX 설계
      - 사용자 경험 개선
      - 디자인 시스템 관리
      - 프로토타입 리뷰
    expertise:
      - 인터페이스 디자인
      - 사용성 테스트
      - Figma
      - 디자인 시스템
    phase_triggers: {}
```

**주의사항:**

- `name`은 전체 에이전트 중에서 중복될 수 없습니다. 중복되면 `Duplicate top-level agent name detected` 오류가 발생합니다.
- `responsibilities`와 `expertise`는 에이전트의 system prompt에 반영되어 응답 성격을 결정합니다.

## 3단계: 안건에 Designer를 필수 발언자로 추가하기

Designer가 특정 안건에서 반드시 발언하도록 `config/agendas.yaml`을 수정합니다:

```yaml
agendas:
  - title: "UI/UX 개선 논의"
    description: "현재 사용자 인터페이스의 개선 방향을 논의합니다"
    required_speakers: ["Host", "Designer", "PM"]
  - title: "스프린트 계획"
    description: "다음 스프린트의 작업 항목을 계획합니다"
    required_speakers: ["PM", "Designer"]
```

`required_speakers`에 포함된 에이전트는 해당 안건에서 반드시 한 번 이상 발언하게 됩니다.

## 4단계: 회의 실행하기

```bash
uv run doorae run --project <프로젝트명>
```

회의가 시작되면 안건 진행 상태 패널이 표시되고, Designer가 UI/UX 관점의 의견을 제시하는 것을 확인할 수 있습니다:

```
┌──────────────── 📋 안건 진행 상태 ────────────────┐
│  🔄 1. UI/UX 개선 논의 (Host) [1:30] ← 현재       │
│  ⏳ 2. 스프린트 계획 (PM)                          │
└───────────────────────────────────────────────────┘

[Host]
안녕하세요, 오늘 첫 번째 안건은 UI/UX 개선 논의입니다. @Designer, 현재 인터페이스에 대한 의견을 부탁드립니다.

[Designer]
네, 현재 인터페이스를 분석해 보면 몇 가지 개선이 필요합니다...
```

## 5단계: 계층 구조 에이전트 추가하기 (선택)

Designer 아래에 하위 에이전트를 둘 수도 있습니다. TechLead가 Backend, Frontend를 하위 에이전트로 두는 것처럼, Designer도 하위 전문가를 가질 수 있습니다:

```yaml
  - name: Designer
    role: designer
    responsibilities:
      - UI/UX 설계
      - 디자인 시스템 관리
    expertise:
      - 인터페이스 디자인
      - 디자인 시스템
    phase_triggers: {}
    agents:
      - name: UXResearcher
        role: ux_researcher
        responsibilities:
          - 사용자 리서치
          - 사용성 테스트 설계
        expertise:
          - 사용자 인터뷰
          - A/B 테스트
        phase_triggers: {}
```

이 경우 Designer는 supervisor 역할을 하며, 필요에 따라 UXResearcher에게 업무를 위임합니다.

**하위 에이전트 규칙:**

- 하위 에이전트의 `name`도 전체 에이전트 중 유일해야 합니다.
- 순환 참조(A -> B -> A)가 있으면 `Agent cycle detected` 오류가 발생합니다.
- `is_human: true`인 에이전트는 하위 에이전트를 가질 수 없습니다.

## 다음 단계

- [안건(Agenda) 설정](configure-agendas.md) - 안건 흐름을 더 세밀하게 제어하기
- [MCP Tool 연동](mcp-tool-integration.md) - 에이전트에 외부 도구 연결하기
- [사람이 회의에 참여하기](human-participation.md) - 실제 사용자로 회의에 참여하기
