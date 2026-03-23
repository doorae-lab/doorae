# Event Protocol Reference

소스: `doorae/interfaces/engine.py`, `doorae/server/events.py`, `doorae/server/room.py`

Doorae의 이벤트 시스템은 두 계층으로 구성된다.

1. **MeetingEngineCallback** -- `MeetingEngine`이 LangGraph 이벤트를 해석하여 호출하는 Python Protocol
2. **WebSocket 이벤트** -- 서버가 클라이언트에 전송하는 JSON 메시지

## MeetingEngineCallback Protocol

소스: `doorae/interfaces/engine.py`

`MeetingEngine.run(callback)` 호출 시 다음 메서드가 호출된다. 모든 메서드는 `async`이다.

### on_raw_event

```python
async def on_raw_event(self, event: dict[str, Any]) -> None
```

LangGraph `astream_events`에서 수신한 모든 raw 이벤트에 대해 호출된다.

### on_speaker_changed

```python
async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None
```

새로운 발언자가 시작될 때 호출된다. 같은 speaker의 연속 호출은 억제된다 (이전 턴이 완료된 후 새 턴이 시작되면 재발행).

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `speaker` | `str` | 발언자 이름 |
| `is_delegated` | `bool` | supervisor에 의해 위임된 발언인지 여부 |

### on_token

```python
async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None
```

스트리밍 중 토큰 단위로 호출된다. `participant` 태그가 있는 `on_chat_model_stream` 이벤트에서 추출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `content` | `str` | 토큰 문자열 |
| `speaker` | `str` | 발언자 이름 |
| `is_delegated` | `bool` | 위임 발언 여부 |

### on_turn_completed

```python
async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None
```

한 발언자의 턴이 완료되었을 때 호출된다. LLM이 tool_calls를 반환한 경우(tool-calling 루프 중간)에는 호출되지 않는다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `speaker` | `str` | 발언자 이름 |
| `is_delegated` | `bool` | 위임 발언 여부 |

### on_human_turn_started

```python
async def on_human_turn_started(self, username: str) -> None
```

사람 참여자의 입력 차례가 시작될 때 호출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `username` | `str` | 사람 참여자 이름 |

### on_agenda_updated

```python
async def on_agenda_updated(
    self,
    agendas: list[dict[str, Any]],
    current_idx: int,
) -> None
```

안건 상태가 변경되었을 때 호출된다. `process_response` 노드의 시작과 종료 시점에 발생한다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `agendas` | `list[dict]` | 전체 안건 목록 |
| `current_idx` | `int` | 현재 안건 인덱스 |

### on_meeting_ended

```python
async def on_meeting_ended(
    self,
    agendas: list[dict[str, Any]],
    speaker_counts: dict[str, int],
) -> None
```

워크플로우 스트림이 종료된 후 호출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `agendas` | `list[dict]` | 최종 안건 목록 |
| `speaker_counts` | `dict[str, int]` | 에이전트별 최종 발언 횟수 |

### on_pending_speakers_changed

```python
async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None
```

발언 대기 큐가 변경되었을 때 호출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `pending_speakers` | `list[str]` | 대기 중인 발언자 이름 목록 |

### on_participant_status_changed

```python
async def on_participant_status_changed(self, participant_name: str, status: str) -> None
```

참여자 상태가 이전 값과 달라졌을 때 호출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `participant_name` | `str` | 참여자 이름 |
| `status` | `str` | 새 상태 (`idle`, `speaking`, `tool_calling`, `waiting_input`) |

### on_tool_call

```python
async def on_tool_call(self, name: str, status: str) -> None
```

도구 호출 시작/종료 시 호출된다.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `name` | `str` | 도구 이름 |
| `status` | `str` | `"started"` 또는 `"ended"` |

## WebSocket 이벤트 형식

소스: `doorae/server/events.py`, `doorae/server/room.py`

### 공통 구조

모든 WebSocket 이벤트는 다음 구조를 따른다.

```json
{
  "type": "<event-type>",
  "data": { ... },
  "timestamp": "2025-01-15T10:30:00.000000"
}
```

### Raw 이벤트 (raw 채널)

`event_to_dict()` 함수가 LangGraph 이벤트를 변환한다.

```json
{
  "type": "on_chat_model_stream",
  "timestamp": "2025-01-15T10:30:00.000000",
  "is_delegated": true,
  "metadata": { ... },
  "data": { ... }
}
```

- `type` -- LangGraph 이벤트의 `event` 필드값
- `is_delegated` -- 태그에 `delegated_by:` 접두사가 있으면 `true`
- `metadata`, `data` -- 원본 이벤트의 해당 필드를 JSON 직렬화

### Semantic 이벤트 (semantic 채널)

`format_semantic_event()` 함수가 생성한다. `type`은 `"semantic:<event_type>"` 형식이다.

#### semantic:speaker_changed

```json
{
  "type": "semantic:speaker_changed",
  "data": {
    "speaker": "PM",
    "is_delegated": false
  },
  "timestamp": "..."
}
```

#### semantic:token

```json
{
  "type": "semantic:token",
  "data": {
    "content": "안녕",
    "speaker": "PM",
    "is_delegated": false
  },
  "timestamp": "..."
}
```

#### semantic:turn_completed

```json
{
  "type": "semantic:turn_completed",
  "data": {
    "speaker": "PM",
    "is_delegated": false
  },
  "timestamp": "..."
}
```

#### semantic:human_turn_started

```json
{
  "type": "semantic:human_turn_started",
  "data": {
    "username": "chulsoo"
  },
  "timestamp": "..."
}
```

#### semantic:agenda_updated

```json
{
  "type": "semantic:agenda_updated",
  "data": {
    "agendas": [ ... ],
    "current_idx": 1
  },
  "timestamp": "..."
}
```

#### semantic:meeting_ended

```json
{
  "type": "semantic:meeting_ended",
  "data": {
    "agendas": [ ... ],
    "speaker_counts": { "Host": 5, "PM": 3 }
  },
  "timestamp": "..."
}
```

#### semantic:pending_speakers_changed

```json
{
  "type": "semantic:pending_speakers_changed",
  "data": {
    "pending_speakers": ["PM", "TechLead"]
  },
  "timestamp": "..."
}
```

#### semantic:participant_status_changed

```json
{
  "type": "semantic:participant_status_changed",
  "data": {
    "participant_name": "PM",
    "status": "speaking"
  },
  "timestamp": "..."
}
```

#### semantic:tool_call

```json
{
  "type": "semantic:tool_call",
  "data": {
    "name": "github_list_issues",
    "status": "started"
  },
  "timestamp": "..."
}
```

#### semantic:agent_profiles

워크플로우 시작 직후 한 번 전송된다. 에이전트 프로필 정보 (llm 설정 제외).

```json
{
  "type": "semantic:agent_profiles",
  "data": {
    "top_profiles": {
      "Host": { "name": "Host", "role": "host", ... },
      "PM": { "name": "PM", "role": "project_manager", ... }
    }
  },
  "timestamp": "..."
}
```

#### semantic:state_snapshot

신규 접속자에게 현재 회의 상태를 전송한다.

```json
{
  "type": "semantic:state_snapshot",
  "data": {
    "current_speaker": "PM",
    "current_delegated_speaker": null,
    "agendas": [ ... ],
    "current_agenda_idx": 1,
    "pending_speakers": ["TechLead"],
    "speaker_counts": { "Host": 3, "PM": 2 },
    "participant_statuses": { "Host": "idle", "PM": "speaking" },
    "top_profiles": { ... }
  },
  "timestamp": "..."
}
```

### 시스템 이벤트

`format_system_event()` 함수가 생성한다.

```json
{
  "type": "system",
  "data": {
    "message": "chulsoo님이 입장했습니다."
  },
  "timestamp": "..."
}
```

### 메시지 이벤트

`format_message_event()` 함수가 생성한다. 사용자 채팅 메시지.

```json
{
  "type": "message",
  "data": {
    "content": "메시지 내용",
    "sender": "chulsoo"
  },
  "timestamp": "..."
}
```

### 에러 이벤트

`format_error_event()` 함수가 생성한다. 특정 사용자에게만 전송된다.

```json
{
  "type": "error",
  "data": {
    "error": "잘못된 JSON 형식입니다."
  },
  "timestamp": "..."
}
```

### 기타 semantic 이벤트

| 이벤트 | 발생 시점 | 데이터 |
|--------|-----------|--------|
| `semantic:user_joined` | 새 사용자 입장 | `username`, `role` |
| `semantic:participants_list` | 신규 접속자에게 기존 참가자 목록 전송 | `participants` (배열) |
