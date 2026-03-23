# System Overview

이 문서는 사용자의 입력이 어떻게 AI 에이전트의 발언으로 변환되는지, 전체 데이터 흐름을 설명한다.

## 데이터 흐름

```mermaid
sequenceDiagram
    participant User as 사용자 (CLI/TUI/WebSocket)
    participant Engine as MeetingEngine
    participant WF as LangGraph Workflow
    participant Refill as RefillSpeakersNode
    participant Dispatch as DispatchNode
    participant Agent as AgentNodeExecutor
    participant LLM as LLM Provider
    participant MCP as MCP Tools
    participant Process as ProcessResponseNode
    participant Router as condition_router

    User->>Engine: 초기 메시지 ("회의를 시작합니다")
    Engine->>Engine: setup() - 프로필 로드, 워크플로우 생성
    Engine->>WF: astream_events(initial_state)

    WF->>Refill: 진입점 (pending_speakers 비어있음)
    Refill-->>WF: pending_speakers = [미발언자들]
    WF->>Router: condition_router(state)
    Router-->>WF: "participant" (pending 있음)

    WF->>Dispatch: pending_speakers[0] 조회
    Dispatch->>Agent: AI 에이전트인 경우
    Agent->>LLM: 프롬프트 + 컨텍스트
    Agent->>MCP: 필요시 도구 호출
    LLM-->>Agent: 응답 생성
    Agent-->>Dispatch: AIMessage + 상태 업데이트
    Dispatch-->>WF: messages, participant_statuses

    WF->>Process: 응답 후처리
    Process->>Process: @멘션 추출, 안건 완료 감지
    Process-->>WF: pending_speakers, speaker_counts 등

    WF->>Router: condition_router(state)
    Router-->>WF: 다음 노드 결정

    WF-->>Engine: 스트리밍 이벤트
    Engine-->>User: 실시간 토큰 스트리밍
```

## 컴포넌트 관계

```mermaid
graph LR
    subgraph Config["설정"]
        Settings["Settings<br/>(pydantic-settings)"]
        Profiles["agent_profiles.yaml"]
        Agendas["agendas.yaml"]
        MCPConfig["mcp_servers.json"]
    end

    subgraph Core["코어 모델"]
        AP["AgentProfile"]
        MS["MeetingState<br/>(MessagesState 확장)"]
        PR["ParticipantRegistry"]
    end

    subgraph LLM["LLM 팩토리"]
        MainLLM["create_main_llm()<br/>temperature=0.7"]
        TaskLLM["create_task_llm()<br/>temperature=0.0"]
        AgentLLM["create_agent_llm()<br/>프로필별 설정"]
    end

    Profiles --> AP
    Settings --> MainLLM
    Settings --> TaskLLM
    AP --> AgentLLM
    AP --> PR
    Agendas --> MS
    MCPConfig --> MCP["MCP Client"]
```

## 계층 구조

Doorae는 5개의 명확한 계층으로 구성된다.

### 1. 인터페이스 계층 (`doorae/interfaces/`, `doorae/server/`)

사용자와의 접점. CLI, TUI, WebSocket Server 세 가지 어댑터가 존재하며, 모두 동일한 `MeetingEngine`을 사용한다.

- **CLI** (`cli.py`): 터미널 기반, `CliInputProvider`로 stdin 입력
- **TUI** (`tui.py`): Textual 프레임워크 기반 리치 UI, `TuiInputProvider`로 이벤트 기반 입력
- **Server** (`server/`): FastAPI + WebSocket, `QueueInputProvider`로 비동기 큐 입력

### 2. 엔진 계층 (`doorae/interfaces/engine.py`)

`MeetingEngine` 클래스가 워크플로우 설정과 이벤트 디스패치를 담당한다. `MeetingEngineCallback` Protocol을 통해 인터페이스 계층에 이벤트를 전달한다.

### 3. 그래프 계층 (`doorae/graph/`)

LangGraph `StateGraph`를 구성하고 실행한다. 핵심 파일:

| 파일 | 역할 |
|------|------|
| `workflow.py` | `create_meeting_workflow()` -- 그래프 빌드 |
| `state.py` | `MeetingState` -- 공유 상태 스키마 |
| `nodes/` | 각 노드 구현 |
| `mediation.py` | Host 중재 컨텍스트 생성 |

### 4. 에이전트 계층 (`doorae/agents/`)

`BaseAgent`가 LLM과 MCP 도구를 통합한다. tool-calling 루프(최대 50회 반복)를 내장하여 도구 호출 → 결과 수집 → 최종 응답 생성까지를 자체 처리한다.

### 5. 코어 계층 (`doorae/core/`, `doorae/config/`)

프로필 시스템, 설정 관리, 날짜 컨텍스트 등 도메인 독립적 기반 코드.

## 실행 모드

| 모드 | 명령어 | InputProvider | 특징 |
|------|--------|---------------|------|
| CLI | `doorae run` | `CliInputProvider` | 터미널 stdin, prompt_toolkit |
| TUI | `doorae run` (기본) | `TuiInputProvider` | Textual 위젯, asyncio.Event 동기화 |
| Server | `doorae serve` | `QueueInputProvider` | asyncio.Queue, WebSocket 브릿지 |
