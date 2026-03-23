# Meeting State Reference

소스: `doorae/graph/state.py`

`MeetingState`는 `langgraph.graph.MessagesState`를 확장한 TypedDict이다. LangGraph 워크플로우의 전체 상태를 담는다.

## MessagesState 상속 필드

`MessagesState`에서 상속된 `messages` 필드가 대화 메시지 히스토리를 보관한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `messages` | `list[BaseMessage]` | LangChain 메시지 히스토리. Annotated reducer로 메시지가 누적된다 |

## 안건 관리

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `agendas` | `List[dict]` | `[]` | Agenda 리스트. 각 원소는 `Agenda` 모델의 dict 표현 |
| `current_agenda_idx` | `int` | `0` | 현재 진행 중인 안건의 인덱스 |
| `pending_proposals` | `List[dict]` | `[]` | 안건 후보 큐. Host 승인을 대기하는 안건 제안 목록 |

## 발언자 큐

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `pending_speakers` | `List[str]` | `[]` | 발언 대기 큐. 에이전트 이름 목록 (예: `["PM", "Designer"]`) |
| `participants` | `Dict[str, str]` | `{}` | 참여자 이름 -> 역할 매핑 |

## 발언 추적

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `speaker_counts` | `Dict[str, int]` | `{}` | 에이전트별 누적 발언 횟수 |
| `participant_statuses` | `Dict[str, str]` | `{}` | 참여자별 현재 상태. `ParticipantStatus` 값 사용 |

## ParticipantStatus

| 값 | 설명 |
|----|------|
| `"idle"` | 대기 중 |
| `"speaking"` | 발언 중 |
| `"tool_calling"` | 도구 호출 중 |
| `"waiting_input"` | 입력 대기 |

## Host 위임 추적

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `consecutive_host_delegations` | `int` | `0` | 연속 Host 위임 횟수 (무한루프 방지) |

## 턴 관리

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `turn_count` | `int` | `0` | 현재까지의 턴 수 |
| `max_turns` | `int` | `1000` | 최대 턴 수. 초과 시 회의 강제 종료 |
| `current_agenda_start_turn` | `int` | `0` | 현재 안건 시작 시점의 턴 번호. Host 중재 n-gram 범위 계산에 사용 |

## 회의 종료

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `meeting_ended` | `bool` | `False` | `True`이면 회의가 종료된 상태 |

## 대화 요약

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `summary` | `Any` | `None` | 대화 요약 (langmem RunningSummary 또는 `None`) |

## 메타데이터

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `start_time` | `float` | `0.0` | 회의 시작 시간 (Unix timestamp) |

## AgentInfo 모델

`participants` 딕셔너리와 별도로, 에이전트의 기본 정보를 표현하는 보조 모델이다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | `str` | 에이전트 이름 |
| `role` | `str` | 역할 |
| `profile_key` | `str` | `agent_profiles.yaml`의 키 |
