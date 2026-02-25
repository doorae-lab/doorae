# WebSocket 채팅

- 상위: [서버-인터페이스](./__init__.md) - 회의 서버의 외부 인터페이스 정의
- 상태: done
- 작성일: 2026-02-25

## 개요

WebSocket 기반 실시간 채팅 인터페이스. 회의방 참가자 간 메시지 교환 및 LangGraph 워크플로우 이벤트 스트리밍을 처리한다.

## 관련 코드

- `thetable/server/routes.py` - WebSocket 엔드포인트
- `thetable/server/room.py` - 메시지 처리, 워크플로우 스트리밍
- `thetable/server/connection_manager.py` - 연결 관리, broadcast
- `thetable/server/events.py` - 이벤트 변환 유틸리티

## 접속

```
WS /ws/{room_id}?username={username}
```

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|---------|------|------|------|------|
| `room_id` | path | string | O | 회의방 ID |
| `username` | query | string | O | 사용자 이름 |

연결 실패 시 WebSocket close code `4004` (회의방 없음)로 종료.

## 메시지 프로토콜

### 클라이언트 -> 서버

JSON 텍스트 메시지:

```json
{
  "content": "메시지 내용"
}
```

- 잘못된 JSON 전송 시 발신자에게 `error` 이벤트 개인 전송

### 서버 -> 클라이언트

모든 이벤트는 아래 공통 구조를 따른다:

```json
{
  "type": "<이벤트 타입>",
  "data": { ... },
  "timestamp": "ISO 8601"
}
```

## 이벤트 타입

| type | 전송 방식 | data 필드 | 설명 |
|------|----------|-----------|------|
| `message` | broadcast | `content`, `sender` | 사용자 채팅 메시지 |
| `system` | broadcast | `message` | 입장/퇴장/워크플로우 시작 알림 |
| `error` | personal 또는 broadcast | `error` | 에러 메시지 |
| `on_chain_start`, `on_chain_end` 등 | broadcast | LangGraph 이벤트 데이터 | AI 워크플로우 스트리밍 이벤트 |

### 이벤트 예시

```json
// message
{
  "type": "message",
  "data": { "content": "안녕하세요", "sender": "Alice" },
  "timestamp": "2026-02-25T15:30:45.123456"
}

// system
{
  "type": "system",
  "data": { "message": "Alice님이 입장했습니다." },
  "timestamp": "2026-02-25T15:30:45.123456"
}

// error (개인 전송)
{
  "type": "error",
  "data": { "error": "잘못된 JSON 형식입니다." },
  "timestamp": "2026-02-25T15:30:45.123456"
}

// LangGraph 워크플로우 이벤트 (broadcast)
{
  "type": "on_chain_start",
  "data": { ... },
  "metadata": { ... },
  "timestamp": "2026-02-25T15:30:45.123456"
}
```

## 연결 생명주기

1. 클라이언트가 `WS /ws/{room_id}?username={username}`으로 연결
2. 서버가 연결 수락 후 `system` 이벤트 (입장 알림) broadcast
3. 클라이언트가 `{"content": "..."}` 형식으로 메시지 전송
4. 서버가 `message` 이벤트로 전체 참가자에게 broadcast
5. 워크플로우 실행 중이면 사용자 입력이 AI 워크플로우 큐로 전달
6. 연결 해제 시 `system` 이벤트 (퇴장 알림) broadcast

## 워크플로우 연동

워크플로우가 시작되면(`POST /api/rooms/{room_id}/start`):

- 참가자별 `asyncio.Queue`가 생성됨
- 클라이언트 메시지의 `content`가 해당 사용자 큐에 추가됨
- 워크플로우가 큐에서 사용자 입력을 비동기로 읽어 처리
- 워크플로우의 `astream_events` (v2) 출력이 JSON 변환되어 전체 참가자에게 broadcast

## 연결 관리

- `ConnectionManager`가 `{username: WebSocket}` 매핑을 관리
- broadcast 중 개별 연결 실패 시 해당 사용자만 정리, 나머지 전송 계속
- 사용자 퇴장 시 WebSocket 연결 + 입력 큐 모두 정리
