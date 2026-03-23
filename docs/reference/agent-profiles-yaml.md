# Agent Profiles YAML Reference

소스: `doorae/core/profile.py`

`agent_profiles.yaml` 파일은 회의 참여자(agent)의 역할, 전문성, 계층 구조를 정의한다. 최상위 키는 `agents`이며 `AgentProfile` 목록을 포함한다.

## AgentProfile 필드

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `name` | `str` | O | | 에이전트 이름. 전체 프로필 트리에서 유일해야 한다 |
| `role` | `str` | O | | 역할 식별자 (예: `host`, `project_manager`, `tech_lead`) |
| `responsibilities` | `List[str]` | O | | 담당 업무 목록 |
| `expertise` | `List[str]` | O | | 전문 분야 목록 |
| `phase_triggers` | `Dict[str, str]` | | `{}` | phase 이름과 자동 발언 프롬프트 매핑 |
| `mcp_tools` | `List[str]` | | `[]` | 사용할 MCP 서버 이름 목록 (예: `["github"]`) |
| `metadata` | `Dict[str, Any]` | | `{}` | Agent별 메타데이터. `additional_instructions`, `target_repository` 등 자유 형식 |
| `llm` | `AgentLLMConfig` | | `None` | 에이전트별 LLM 설정 override |
| `agents` | `List[AgentProfile]` | | `None` | 하위 에이전트 목록 (재귀적 구조). 설정하면 supervisor로 동작 |
| `is_human` | `bool` | | `False` | `true`이면 사람 참여자. `is_human=true`이면서 `agents`가 설정되면 `agents`는 무시된다 |

## AgentLLMConfig 필드

에이전트별 LLM 설정을 override한다. 모든 필드는 선택 사항이며, `None`이면 전역 Settings의 Main LLM 설정을 사용한다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `model` | `Optional[str]` | `None` | 모델명 |
| `api_key` | `Optional[str]` | `None` | API 키. `${ENV_VAR}` 형식의 환경 변수 참조 지원 |
| `base_url` | `Optional[str]` | `None` | Base URL. `${ENV_VAR}` 형식의 환경 변수 참조 지원 |
| `temperature` | `Optional[float]` | `None` | Temperature |
| `max_tokens` | `Optional[int]` | `None` | 최대 토큰 |

`api_key`, `base_url`, `model` 필드에서 `${VAR}` 패턴은 `os.environ`의 값으로 치환된다. 환경 변수가 설정되지 않으면 `None`이 된다.

## 계층 구조

`agents` 필드를 통해 supervisor-worker 계층을 구성할 수 있다. Supervisor 에이전트는 하위 에이전트에 작업을 위임한다.

- `AgentProfile.is_supervisor()` -- `agents`가 비어 있지 않으면 `True`
- `AgentProfile.get_child_names()` -- 하위 에이전트 이름 목록 반환
- `AgentProfile.matches_phase(phase)` -- `phase_triggers`에 해당 phase가 있으면 `True`

순환 참조는 `validate_no_cycles()`에서 검증되며 탐지 시 `ValueError`가 발생한다. 전체 트리에서 이름 중복이 있으면 `ValueError`가 발생한다.

## 전체 예시

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
    phase_triggers: {}
    metadata:
      additional_instructions: |
        회의 종료 시에만 "회의를 종료합니다" 발언 가능.

  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 이슈 상태 관리
      - 진행 상황 보고
    expertise:
      - 일정 계획
      - 자원 관리
    mcp_tools:
      - github
    metadata:
      target_repository: "my-org/my-repo"
      additional_instructions: |
        도구를 적극적으로 사용하세요.

  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
      - 아키텍처 설계
    expertise:
      - 시스템 설계
      - 성능 최적화
    phase_triggers:
      issue_resolution: "기술적 해결 방안을 제시하세요"
    mcp_tools:
      - github
    metadata:
      target_repository: "my-org/my-repo"
    llm:
      model: "gpt-4o"
      api_key: "${OPENAI_API_KEY}"
      base_url: "${OPENAI_BASE_URL}"
      temperature: 0.2
      max_tokens: 3000
    agents:
      - name: Backend
        role: backend_engineer
        responsibilities:
          - API 설계 및 구현
          - 데이터베이스 최적화
        expertise:
          - Python
          - FastAPI
        phase_triggers: {}
      - name: Frontend
        role: frontend_engineer
        responsibilities:
          - UI 컴포넌트 구현
          - 사용자 경험 최적화
        expertise:
          - React
          - TypeScript
        phase_triggers: {}

  # 사람 참여자
  - name: chulsoo
    role: backend_engineer
    is_human: true
    responsibilities:
      - 백엔드 아키텍처 의견 제시
    expertise:
      - Python
      - FastAPI
    phase_triggers: {}
```
