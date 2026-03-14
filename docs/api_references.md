# API Reference

> 전체 API 엔드포인트 목록. 각 기능별 상세 스펙은 `.specs/` 디렉토리의 개별 문서를 참고한다.
>
> 섹션 1~5는 미구현 설계 스펙, 섹션 6~8은 구현 완료된 인터페이스이다.

Base URL: `/api`

---

## 1. 인증 (Auth) (미구현)

> 스펙: `.specs/user/106-유저-관리/113-회원가입로그인.md`, `133-회원가입로그인-화면.md`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `POST` | `/api/auth/register` | 회원가입 | #113, #133 |
| `POST` | `/api/auth/login` | 로그인 (JWT 발급) | #113, #133 |

---

## 2. 프로젝트 관리 (Project) (미구현)

> 스펙: `.specs/project/134-프로젝트-관리/131-프로젝트-관리-Web_API.md`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `POST` | `/api/projects` | 프로젝트 생성 | #131 |
| `GET` | `/api/projects` | 프로젝트 목록 조회 | #131 |
| `GET` | `/api/projects/{id}` | 프로젝트 상세 조회 | #131 |
| `PATCH` | `/api/projects/{id}` | 프로젝트 수정 | #131 |
| `DELETE` | `/api/projects/{id}` | 프로젝트 삭제/아카이브 | #131 |

### Query Parameters (목록 조회)

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `page` | int | 1 | 페이지 번호 |
| `limit` | int | 20 | 페이지 당 개수 |
| `status` | string | - | 상태 필터 (`active`, `archived`) |

---

## 3. 에이전트 프로필 (Profile) (미구현)

> 스펙: `.specs/agent/105-에이전트-기능/`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `GET` | `/api/profiles` | 에이전트 프로필 목록 조회 | #112, #114 |
| `GET` | `/api/profiles/{id}` | 에이전트 프로필 상세 조회 | #112, #114 |

---

## 4. 미팅 (Meeting) (미구현)

> 스펙: `.specs/project/107-프로젝트-기능-미팅/`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `POST` | `/api/projects/{id}/meetings` | 미팅 생성 | #108 |
| `GET` | `/api/projects/{id}/meetings` | 미팅 목록 조회 | #107 |
| `GET` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 상세 조회 | #108 |
| `PATCH` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 수정 | #108 |
| `DELETE` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 취소 | #109 |

---

## 5. 안건 (Agenda) (미구현)

> 스펙: `.specs/project/107-프로젝트-기능-미팅/110-미팅-안건-crud.md`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `GET` | `/api/agendas/templates` | 안건 템플릿 목록 (Optional) | #110 |
| `GET` | `/api/projects/{id}/meetings/{mid}/agendas` | 안건 목록 조회 | #110 |
| `POST` | `/api/projects/{id}/meetings/{mid}/agendas` | 안건 추가 | #110 |
| `PUT` | `/api/projects/{id}/meetings/{mid}/agendas/{aid}` | 안건 수정 | #110 |
| `DELETE` | `/api/projects/{id}/meetings/{mid}/agendas/{aid}` | 안건 삭제 | #110 |

---

## 6. 회의방 (Room)

> 구현: `doorae/server/routes.py`, `doorae/server/room.py`

| 메서드 | 엔드포인트 | 설명 | 상태 |
|--------|-----------|------|------|
| `POST` | `/api/rooms` | 회의방 생성 | 구현 |
| `GET` | `/api/rooms` | 회의방 목록 조회 | 구현 |
| `GET` | `/api/rooms/{room_id}` | 회의방 상세 조회 | 구현 |
| `DELETE` | `/api/rooms/{room_id}` | 회의방 삭제 | 구현 |
| `POST` | `/api/rooms/{room_id}/start` | AI 워크플로우 시작 | 구현 |

### Request/Response 모델

**RoomCreate** (POST `/api/rooms` 요청 본문)

| 필드 | 타입 | 필수 | 제약 | 설명 |
|------|------|------|------|------|
| `name` | string | O | 1~100자 | 회의방 이름 |
| `agenda` | string | X | 최대 500자 | 회의 안건 |

**RoomInfo** (응답 모델)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 회의방 ID |
| `name` | string | 회의방 이름 |
| `agenda` | string \| null | 회의 안건 |
| `created_at` | datetime | 생성 시간 |
| `participants_count` | int | 현재 참가자 수 |

### 에러 응답

| 상태 코드 | 조건 |
|-----------|------|
| `400` | 회의방 생성 실패 (max_rooms 초과 등) |
| `400` | 워크플로우 시작 시 참가자 없음 |
| `404` | 존재하지 않는 room_id |
| `409` | 워크플로우가 이미 실행 중 |

---

## 7. WebSocket

> 구현: `doorae/server/routes.py`, `doorae/server/connection_manager.py`

### 접속

```
WS /ws/{room_id}?username={username}
```

| 파라미터 | 위치 | 타입 | 필수 | 설명 |
|---------|------|------|------|------|
| `room_id` | path | string | O | 회의방 ID |
| `username` | query | string | O | 사용자 이름 |

연결 실패 시 WebSocket close code `4004` (회의방 없음)로 종료.

### 클라이언트 → 서버

JSON 텍스트 메시지:

```json
{
  "content": "메시지 내용"
}
```

### 서버 → 클라이언트

모든 이벤트는 아래 공통 구조를 따른다:

```json
{
  "type": "<이벤트 타입>",
  "data": { ... },
  "timestamp": "ISO 8601"
}
```

#### 이벤트 타입

| type | 방향 | data 필드 | 설명 |
|------|------|-----------|------|
| `message` | broadcast | `content`, `sender` | 사용자 채팅 메시지 |
| `system` | broadcast | `message` | 입장/퇴장/워크플로우 시작 알림 |
| `error` | personal 또는 broadcast | `error` | 에러 메시지 |
| `on_chain_start`, `on_chain_end` 등 | broadcast | LangGraph 이벤트 데이터 | AI 워크플로우 스트리밍 이벤트 |

#### 이벤트 예시

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

### 연결 생명주기

1. 클라이언트가 `WS /ws/{room_id}?username={username}`으로 연결
2. 서버가 연결 수락 후 `system` 이벤트 (입장 알림) broadcast
3. 클라이언트가 `{"content": "..."}` 형식으로 메시지 전송
4. 서버가 `message` 이벤트로 전체 참가자에게 broadcast
5. 워크플로우 실행 중이면 사용자 입력이 AI 워크플로우 큐로 전달
6. 연결 해제 시 `system` 이벤트 (퇴장 알림) broadcast

---

## 8. 서버 설정

> 구현: `doorae/server/config.py`

환경 변수 prefix: `SERVER_` (`DOORAE_SERVER` 예외 지원)

| 환경 변수 | 타입 | 기본값 | 설명 |
|-----------|------|-------|------|
| `DOORAE_SERVER` | string | — | `host:port` 형식의 통합 바인드 주소. 설정 시 `SERVER_HOST`/`SERVER_PORT`보다 우선 |
| `SERVER_HOST` | string | `0.0.0.0` | 바인드 주소 |
| `SERVER_PORT` | int | `8000` | 바인드 포트 |
| `SERVER_MAX_ROOMS` | int | `100` | 최대 동시 회의방 수 |
