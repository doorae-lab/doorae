# Server API Reference

소스: `doorae/server/routes.py`, `doorae/server/models.py`, `doorae/server/room.py`, `doorae/server/connection_manager.py`

Doorae 서버는 FastAPI 기반이다. REST API로 회의방을 관리하고, WebSocket으로 실시간 회의에 참여한다.

서버 시작: `doorae serve -s 0.0.0.0:8000`

## REST API

### POST /api/rooms

회의방을 생성한다.

**Request Body** (`RoomCreate`):

| 필드 | 타입 | 필수 | 제약 | 설명 |
|------|------|------|------|------|
| `name` | `str` | O | 1~100자 | 회의방 이름 |
| `agenda` | `str \| null` | | 최대 500자 | 회의 안건 |

**Response** (201, `RoomInfo`):

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | `str` | 회의방 UUID |
| `name` | `str` | 회의방 이름 |
| `agenda` | `str \| null` | 회의 안건 |
| `created_at` | `datetime` | 생성 시간 (ISO 8601) |
| `participants_count` | `int` | 현재 참여자 수 |

**Error**:

| 코드 | 조건 |
|------|------|
| 400 | 최대 회의방 수 (기본 100) 초과 |

```json
// Request
POST /api/rooms
{
  "name": "Sprint Planning",
  "agenda": "이번 스프린트 계획 수립"
}

// Response 201
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sprint Planning",
  "agenda": "이번 스프린트 계획 수립",
  "created_at": "2025-01-15T10:30:00",
  "participants_count": 0
}
```

### GET /api/rooms

모든 회의방 목록을 조회한다.

**Response** (200, `list[RoomInfo]`):

RoomInfo 객체 배열.

```json
// Response 200
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Sprint Planning",
    "agenda": "이번 스프린트 계획 수립",
    "created_at": "2025-01-15T10:30:00",
    "participants_count": 2
  }
]
```

### GET /api/rooms/{room_id}

특정 회의방 정보를 조회한다.

**Path Parameter**:

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `room_id` | `str` | 회의방 UUID |

**Response** (200, `RoomInfo`)

**Error**:

| 코드 | 조건 |
|------|------|
| 404 | 회의방을 찾을 수 없음 |

### DELETE /api/rooms/{room_id}

회의방을 삭제한다.

**Path Parameter**:

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `room_id` | `str` | 회의방 UUID |

**Response**: 204 (No Content)

**Error**:

| 코드 | 조건 |
|------|------|
| 404 | 회의방을 찾을 수 없음 |

### POST /api/rooms/{room_id}/start

회의방의 AI 워크플로우를 시작한다. WebSocket으로 연결된 참가자가 1명 이상이어야 한다.

**Path Parameter**:

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `room_id` | `str` | 회의방 UUID |

**Response** (200):

```json
{
  "status": "started",
  "room_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error**:

| 코드 | 조건 |
|------|------|
| 404 | 회의방을 찾을 수 없음 |
| 409 | 워크플로우가 이미 실행 중 |
| 400 | 참가자가 없음 |

## WebSocket

### WS /ws/{room_id}

회의방에 WebSocket으로 연결한다.

**Path Parameter**:

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `room_id` | `str` | 회의방 UUID |

**Query Parameter**:

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `username` | `str` (필수) | | 사용자 이름 |
| `raw_events` | `bool` | `True` | raw LangGraph 이벤트 수신 여부 |

**연결 실패**:

| WebSocket 코드 | 조건 |
|----------------|------|
| 4004 | 회의방을 찾을 수 없음 |

### 클라이언트 -> 서버 메시지

JSON 형식으로 전송한다.

```json
{
  "content": "메시지 내용"
}
```

현재 입력 차례가 아닌 사용자가 메시지를 보내면 error 이벤트가 개인에게 전송된다.

### 서버 -> 클라이언트 이벤트

모든 이벤트는 JSON 형식이다. [Event Protocol](event-protocol.md) 페이지에서 전체 이벤트 목록을 확인할 수 있다.

#### 채널

서버는 이벤트를 두 채널로 분리하여 브로드캐스트한다.

| 채널 | 설명 | 수신 조건 |
|------|------|-----------|
| `raw` | LangGraph raw 이벤트를 JSON 변환한 것 | `raw_events=True`로 연결 |
| `semantic` | 구조화된 semantic 이벤트 | 항상 수신 |

#### 연결 시 자동 전송 이벤트

1. **participants_list** -- 기존 참가자 목록 (신규 접속자 본인에게만)
2. **state_snapshot** -- 워크플로우 실행 중이면 현재 회의 상태 스냅샷 (신규 접속자 본인에게만)
3. **user_joined** 또는 재연결 메시지 -- 전체 참가자에게 브로드캐스트

#### 연결 해제 시

WebSocket 연결이 끊기면 입력 큐는 보존되고 재연결을 기다린다. 재연결 시 기존 큐를 재사용한다.
