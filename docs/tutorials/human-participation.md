# 사람이 회의에 참여하기

이 튜토리얼에서는 `is_human: true`를 설정하여 실제 사용자가 AI 에이전트와 함께 회의에 참여하는 방법을 안내합니다.

## 사전 준비

- [프로젝트 워크스페이스](project-workspace.md) 튜토리얼을 완료한 상태
- `.env`에 API key가 설정된 상태

## 1단계: 사람 참여자 프로필 추가하기

프로젝트의 `config/agent_profiles.yaml`에 `is_human: true`를 설정한 프로필을 추가합니다:

```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 시작 인사 및 안건 소개
      - 안건 진행 상황 관리
      - 회의 요약 및 마무리
    expertise:
      - 회의 퍼실리테이션
    phase_triggers: {}

  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 이슈 상태 관리
    expertise:
      - 일정 계획
      - 자원 관리

  - name: chulsoo
    role: backend_engineer
    is_human: true
    responsibilities:
      - 백엔드 아키텍처 의견 제시
      - 기술적 리스크 검토
    expertise:
      - Python
      - FastAPI
      - PostgreSQL
    phase_triggers: {}
```

**`is_human: true`의 효과:**

- 이 에이전트의 차례가 오면 LLM 대신 사용자에게 입력을 요청합니다.
- `responsibilities`와 `expertise`는 다른 AI 에이전트가 이 참여자의 역할을 이해하는 데 사용됩니다.
- `is_human: true`인 에이전트는 하위 에이전트(`agents` 필드)를 가질 수 없습니다. 설정하면 무시되며 경고가 출력됩니다.

## 2단계: 안건에 사람 참여자 배정하기

`config/agendas.yaml`에서 `required_speakers`에 사람 참여자의 이름을 추가합니다:

```yaml
agendas:
  - title: "백엔드 아키텍처 리뷰"
    description: "현재 백엔드 아키텍처의 문제점과 개선 방향을 논의합니다"
    required_speakers: ["Host", "PM", "chulsoo"]
  - title: "스프린트 계획"
    description: "다음 스프린트의 작업 항목을 계획합니다"
    required_speakers: ["PM"]
```

## 3단계: 회의 실행하기

```bash
uv run doorae run --project <프로젝트명>
```

## 4단계: 사람 차례에 입력하기

회의가 진행되다가 `chulsoo`의 차례가 오면 다음과 같은 입력 프롬프트가 표시됩니다:

```
============================================================
[chulsoo님 차례입니다]

📋 현재 안건: 백엔드 아키텍처 리뷰
   설명: 현재 백엔드 아키텍처의 문제점과 개선 방향을 논의합니다

💬 최근 발언:
   [Host] 백엔드 아키텍처 리뷰를 시작하겠습니다...
   [PM] 현재 API 응답 시간이 증가하는 추세입니다...

============================================================
💡 의견을 입력하세요 (빈 입력 시 스킵):
>
```

이 상태에서 의견을 입력하면 됩니다:

```
> @TechLead 현재 데이터베이스 쿼리 최적화가 필요하다고 생각합니다. 특히 N+1 문제가 있습니다.
```

**입력 팁:**

- `@Name` 형식으로 다른 에이전트를 호출하면, 해당 에이전트가 다음에 발언합니다.
- 빈 입력(Enter만 누르기)을 하면 발언을 건너뜁니다.
- 입력한 내용은 다른 AI 에이전트에게 전달되어 후속 논의에 반영됩니다.

## 5단계: 이후 회의 흐름 관찰하기

입력 후 AI 에이전트들이 사람의 의견을 참고하여 논의를 이어갑니다:

```
[TechLead]
@chulsoo님이 지적하신 N+1 문제는 중요한 포인트입니다.
@Backend, 현재 ORM 사용 패턴을 검토해 주세요.

  ↳ Backend (위임)
  네, 확인해 보겠습니다. 현재 SQLAlchemy에서 lazy loading이
  기본으로 설정되어 있어 N+1 쿼리가 발생하고 있습니다...
```

## TUI 모드에서의 입력

TUI 모드(기본값)에서는 화면 하단의 입력 필드를 통해 의견을 입력합니다. Classic CLI 모드에서는 위에서 설명한 텍스트 기반 프롬프트가 표시됩니다.

TUI 대신 Classic CLI를 사용하려면:

```bash
uv run doorae run --project <프로젝트명> --classic
```

## 여러 사람이 참여하기

여러 사람 참여자를 추가할 수도 있습니다:

```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 진행
    expertise:
      - 퍼실리테이션

  - name: chulsoo
    role: backend_engineer
    is_human: true
    responsibilities:
      - 백엔드 개발
    expertise:
      - Python

  - name: younghee
    role: frontend_engineer
    is_human: true
    responsibilities:
      - 프론트엔드 개발
    expertise:
      - React
```

단, 로컬 CLI 모드에서는 같은 터미널에서 순서대로 입력하게 됩니다. 여러 사람이 각자의 터미널에서 참여하려면 [Server 모드](server-mode-multiplayer.md)를 사용하세요.

## 다음 단계

- [Server 모드와 멀티플레이어](server-mode-multiplayer.md) - 각자의 터미널에서 회의 참여하기
- [커스텀 에이전트 프로필](custom-agent-profiles.md) - 에이전트 역할 세밀하게 정의하기
