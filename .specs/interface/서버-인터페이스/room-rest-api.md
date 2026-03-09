# Room REST API

- 상위: [서버-인터페이스](./__init__.md) - 회의 서버의 외부 인터페이스 정의
- 상태: done
- 작성일: 2026-02-25

## 개요

회의방(Room)의 생성, 조회, 삭제 및 AI 워크플로우 시작을 위한 REST API.

## 관련 코드

- `doorae/server/routes.py`
- `doorae/server/room.py`
- `doorae/server/room_manager.py`
- `doorae/server/models.py`
- `doorae/server/config.py`

## 엔드포인트

| 메서드 | 엔드포인트 | 설명 | 상태 코드 |
|--------|-----------|------|-----------|
| `POST` | `/api/rooms` | 회의방 생성 | 201 |
| `GET` | `/api/rooms` | 회의방 목록 조회 | 200 |
| `GET` | `/api/rooms/{room_id}` | 회의방 상세 조회 | 200 |
| `DELETE` | `/api/rooms/{room_id}` | 회의방 삭제 | 204 |
| `POST` | `/api/rooms/{room_id}/start` | AI 워크플로우 시작 | 200 |

## 데이터 모델

### RoomCreate (요청)

| 필드 | 타입 | 필수 | 제약 | 설명 |
|------|------|------|------|------|
| `name` | string | O | 1~100자 | 회의방 이름 |
| `agenda` | string | X | 최대 500자 | 회의 안건 |

### RoomInfo (응답)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 회의방 ID |
| `name` | string | 회의방 이름 |
| `agenda` | string \| null | 회의 안건 |
| `created_at` | datetime | 생성 시간 |
| `participants_count` | int | 현재 참가자 수 |

## 에러 응답

| 상태 코드 | 조건 |
|-----------|------|
| `400` | 회의방 생성 실패 (max_rooms 초과 등) |
| `400` | 워크플로우 시작 시 참가자 없음 |
| `404` | 존재하지 않는 room_id |
| `409` | 워크플로우가 이미 실행 중 |

## 워크플로우 시작 (`POST /api/rooms/{room_id}/start`)

사전 조건:
- 회의방이 존재해야 함
- 1명 이상의 참가자가 WebSocket으로 연결되어 있어야 함
- 워크플로우가 아직 실행 중이지 않아야 함

처리 흐름:
1. 현재 참가자 목록으로 런타임 human 프로필 생성
2. 참가자별 입력 큐(`asyncio.Queue`) 생성
3. `QueueInputProvider`로 입력 큐 연결
4. LangGraph 워크플로우 생성 및 컴파일
5. 백그라운드 태스크로 워크플로우 스트리밍 시작
6. `system` 이벤트로 시작 알림 broadcast

응답:

```json
{
  "status": "started",
  "room_id": "{room_id}"
}
```

## 서버 설정

환경 변수 prefix: `SERVER_`

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|-------|------|
| `SERVER_HOST` | string | `0.0.0.0` | 바인드 주소 |
| `SERVER_PORT` | int | `8000` | 바인드 포트 |
| `SERVER_MAX_ROOMS` | int | `100` | 최대 동시 회의방 수 |
