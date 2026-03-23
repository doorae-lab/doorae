# 서버 운영 가이드

Doorae 서버는 FastAPI + WebSocket 기반으로, 여러 사용자가 동시에 AI 회의에 참여할 수 있는 실시간 채팅 서버입니다.

---

## 서버 시작

### 기본 실행

```bash
doorae serve
```

기본적으로 `0.0.0.0:8000`에 바인딩됩니다.

### 커스텀 주소 바인딩

```bash
doorae serve -s 0.0.0.0:9000
```

또는 환경변수로:

```bash
export DOORAE_SERVER=0.0.0.0:9000
doorae serve
```

### 서버 의존성 설치

서버 모드에는 `fastapi`, `uvicorn`, `starlette` 등 추가 의존성이 필요합니다:

```bash
uv sync --extra server
```

의존성이 없으면 다음 오류가 발생합니다:

```
Server mode requires optional dependencies. Run 'uv sync --extra server'.
```

---

## 환경변수 설정

서버 설정은 `pydantic-settings`를 통해 `.env` 파일 또는 환경변수에서 로딩됩니다.

### ServerSettings

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| `DOORAE_SERVER` | 서버 주소 (host:port). 설정 시 SERVER_HOST, SERVER_PORT를 덮어씀 | `None` |
| `SERVER_HOST` | 바인딩 호스트 | `0.0.0.0` |
| `SERVER_PORT` | 바인딩 포트 | `8000` |
| `SERVER_MAX_ROOMS` | 최대 회의방 수 | `100` |

`DOORAE_SERVER`가 설정되면 `host:port` 형식으로 파싱되어 `SERVER_HOST`와 `SERVER_PORT`를 덮어씁니다.

`.env` 예시:

```env
DOORAE_SERVER=0.0.0.0:8000
SERVER_MAX_ROOMS=50
```

### DOORAE_SERVER 형식 오류

`DOORAE_SERVER` 값이 올바르지 않으면 다음 오류가 발생합니다:

| 오류 메시지 | 원인 |
|-------------|------|
| `DOORAE_SERVER는 비워둘 수 없습니다.` | 빈 문자열 |
| `DOORAE_SERVER에 호스트가 없습니다.` | `:8000` (호스트 누락) |
| `DOORAE_SERVER는 host:port 형식만 지원합니다.` | 잘못된 형식 |
| `DOORAE_SERVER의 포트 번호가 올바르지 않습니다.` | 포트가 숫자가 아님 |
| `DOORAE_SERVER에 포트가 없습니다.` | `localhost` (포트 누락) |

---

## Room Lifecycle

### 1. 회의방 생성

REST API로 회의방을 생성합니다:

```
POST /api/rooms
Content-Type: application/json

{
  "name": "주간 회의",
  "agenda": "스프린트 리뷰 및 계획"
}
```

응답:

```json
{
  "id": "uuid-...",
  "name": "주간 회의",
  "agenda": "스프린트 리뷰 및 계획",
  "created_at": "2024-01-15T10:00:00",
  "participants_count": 0
}
```

CLI를 사용하면 `doorae create -s localhost:8000`이 방 생성 + WebSocket 연결 + 워크플로우 시작을 한 번에 수행합니다.

### 2. 참가자 연결

WebSocket으로 연결합니다:

```
ws://localhost:8000/ws/{room_id}?username=alice&raw_events=true
```

쿼리 파라미터:

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `username` | 사용자 이름 (필수) | |
| `raw_events` | raw LangGraph 이벤트 수신 여부 | `true` |

연결 시 기존 참가자 목록과 현재 상태 snapshot이 전송됩니다.

### 3. 워크플로우 시작

```
POST /api/rooms/{room_id}/start
```

워크플로우 시작 조건:

- 최소 1명의 WebSocket 연결이 있어야 함
- 이미 실행 중인 워크플로우가 없어야 함 (409 Conflict)

워크플로우가 시작되면 모든 참가자에게 system 이벤트가 브로드캐스트됩니다.

### 4. 메시지 송수신

클라이언트 → 서버 (사용자 입력):

```json
{
  "content": "저는 API 우선 접근이 좋다고 생각합니다"
}
```

현재 활성 사용자(`human_turn_started`)가 아닌 사용자가 메시지를 보내면 거부됩니다:

```json
{
  "type": "error",
  "content": "현재 입력할 수 있는 차례가 아닙니다."
}
```

### 5. 재연결

WebSocket 연결이 끊기면:

- 입력 큐는 보존됨 (메시지 유실 방지)
- 다른 참가자에게 오프라인 상태 알림
- 동일 username으로 재연결 시 자동 복구
- 현재 상태 snapshot이 재전송됨

### 6. 회의방 삭제

```
DELETE /api/rooms/{room_id}
```

---

## REST API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/rooms` | 회의방 생성 |
| `GET` | `/api/rooms` | 회의방 목록 조회 |
| `GET` | `/api/rooms/{room_id}` | 회의방 상세 조회 |
| `DELETE` | `/api/rooms/{room_id}` | 회의방 삭제 |
| `POST` | `/api/rooms/{room_id}/start` | 워크플로우 시작 |
| `WebSocket` | `/ws/{room_id}` | 실시간 채팅 연결 |

---

## WebSocket 이벤트 타입

서버에서 클라이언트로 전송되는 주요 이벤트:

### Semantic 이벤트

| 이벤트 타입 | 설명 |
|-------------|------|
| `speaker_changed` | 발언자 변경 |
| `token` | 스트리밍 토큰 |
| `turn_completed` | 발언 완료 |
| `human_turn_started` | 사용자 입력 차례 시작 |
| `agenda_updated` | 안건 상태 변경 |
| `meeting_ended` | 회의 종료 |
| `participant_status_changed` | 참여자 상태 변경 |
| `user_joined` | 사용자 입장 |
| `tool_call` | MCP tool 호출 시작/종료 |
| `agent_profiles` | 에이전트 프로필 정보 (워크플로우 시작 시) |
| `participants_list` | 기존 참가자 목록 (신규 입장 시) |
| `state_snapshot` | 현재 회의 상태 (재연결 시) |

### System 이벤트

입장, 퇴장, 재연결 등의 알림 메시지.

### Error 이벤트

JSON 파싱 실패, 입력 차례 아님 등의 에러 메시지.

---

## 프로덕션 배포 시 고려사항

### CORS 설정

현재 개발 모드에서는 모든 origin을 허용합니다. 프로덕션에서는 `create_app()` 내의 CORS 설정을 제한하세요.

### 리버스 프록시

Nginx/Caddy 뒤에 배치할 때 WebSocket 업그레이드를 허용해야 합니다:

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}

location / {
    proxy_pass http://127.0.0.1:8000;
}
```

### 최대 회의방 수

`SERVER_MAX_ROOMS`를 초과하면 방 생성 시 400 오류가 발생합니다:

```
최대 회의방 수(100)를 초과했습니다.
```

서버 리소스에 맞게 적절한 값을 설정하세요. 각 회의방은 LLM API 호출을 포함하므로 동시 실행 회의방 수에 비례하여 API 비용이 증가합니다.
