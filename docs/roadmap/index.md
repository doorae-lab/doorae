# 로드맵

## 비전: 회의 시스템에서 AI 팀 워크스페이스로

Doorae는 현재 **AI 에이전트가 참여하는 구조화된 회의 시스템**입니다. 하지만 우리의 최종 목표는 AI 에이전트와 사람이 함께 일하는 **자율 협업 워크스페이스**를 만드는 것입니다.

현재의 Doorae는 "회의"라는 단일 상호작용 모델에 집중하고 있습니다. 로드맵은 이 기반 위에 **채널 채팅**, **Web UI**, **멀티 런타임**, **영속 메모리**, **Always-on 에이전트** 등을 쌓아올려, 에이전트가 진정한 팀원처럼 작동하는 환경을 구축하는 것을 목표로 합니다.

## 단계별 계획

```mermaid
gantt
    title Doorae 로드맵
    dateFormat YYYY-Q
    axisFormat %Y-Q%q

    section Phase 1 — MVP
    채널 기반 채팅           :p1a, 2026-Q2, 2026-Q3
    기본 Web UI              :p1b, 2026-Q2, 2026-Q4
    Agent Daemon Bridge      :p1c, 2026-Q2, 2026-Q3

    section Phase 2 — 차별화
    Agent-to-Agent 통신       :p2a, 2026-Q3, 2027-Q1
    계층적 Task 위임          :p2b, 2026-Q4, 2027-Q1
    Task Board               :p2c, 2026-Q4, 2027-Q2
    에이전트 영속 메모리       :p2d, 2026-Q3, 2027-Q1

    section Phase 3 — 플랫폼
    멀티 런타임               :p3a, 2027-Q1, 2027-Q3
    Always-on 에이전트        :p3b, 2027-Q1, 2027-Q3
    다중 머신 지원            :p3c, 2027-Q2, 2027-Q4
```

### Phase 1: MVP

**핵심 가치**: 회의를 넘어, 팀이 실시간으로 소통하는 채널을 제공합니다.

| 기능 | 설명 |
|------|------|
| [채널 기반 채팅](channel-chat.md) | Slack 스타일의 비동기 채널 대화 |
| [Web UI](web-ui.md) | React 기반 웹 인터페이스 |
| [Agent Daemon Bridge](agent-daemon-bridge.md) | 서버와 에이전트 런타임을 연결하는 경량 bridge |

### Phase 2: 차별화

**핵심 가치**: 에이전트가 스스로 협업하고, 작업을 추적하며, 기억을 유지합니다.

| 기능 | 설명 |
|------|------|
| Agent-to-Agent 통신 | 에이전트 간 직접 메시지와 위임 프로토콜 |
| 계층적 Task 위임 | Supervisor가 작업을 분해하고 sub-agent에게 할당 |
| [Task Board](task-board.md) | Kanban 기반 작업 관리, 메시지에서 Task 생성 |
| [에이전트 영속 메모리](persistent-memory.md) | 세션을 넘어 유지되는 장기 기억 |

### Phase 3: 플랫폼

**핵심 가치**: 어떤 AI 프레임워크든, 어떤 머신에서든 에이전트를 실행합니다.

| 기능 | 설명 |
|------|------|
| [멀티 런타임](multi-runtime.md) | OpenHands, Claude Agent SDK 등 다양한 에이전트 실행 백엔드 |
| [Always-on 에이전트](always-on-agents.md) | 회의 세션 없이도 상시 활성 상태의 에이전트 |
| [다중 머신 지원](multi-machine.md) | 분산 환경에서의 에이전트 실행 |

## 현재 상태 vs 목표 상태

| 영역 | 현재 (v0.1) | 목표 |
|------|-------------|------|
| **상호작용 모델** | 회의(Meeting) 단일 모드 | 채널 채팅 + 회의 + Task Board |
| **인터페이스** | CLI / TUI 터미널 | Web UI + CLI + API |
| **에이전트 생명주기** | 회의 시작~종료 | Always-on, hibernate/wake |
| **에이전트 런타임** | LangGraph 단일 런타임 | 멀티 런타임 (OpenHands, Claude SDK 등) |
| **메모리** | 세션 내 대화 컨텍스트 | 영속 메모리 (DB + workspace 파일) |
| **실행 환경** | 단일 머신 | 다중 머신 분산 실행 |
| **통신 방식** | 회의 내 발언 순서 기반 | 비동기 채널 + 직접 메시지 + 위임 |
| **작업 관리** | 없음 | Kanban Task Board + 자동 분해/할당 |

!!! info "기여하기"
    로드맵에 있는 기능에 관심이 있으시면 [GitHub Discussions](https://github.com/doorae-lab/doorae/discussions)에서 의견을 나눠주세요. 각 기능 페이지의 설계에 대한 피드백을 환영합니다.
