# Server 모드와 멀티플레이어

이 튜토리얼에서는 Doorae의 WebSocket 서버를 시작하고, 여러 사용자가 동시에 같은 회의방에 참여하는 멀티플레이어 회의를 진행합니다.

## 사전 준비

- Doorae 설치 완료
- `.env`에 API key가 설정된 상태
- server 의존성 설치:

```bash
uv sync --extra server
```

## 1단계: 서버 시작하기

터미널을 열고 Doorae 서버를 시작합니다:

```bash
uv run doorae serve -s 0.0.0.0:8000
```

서버가 정상적으로 시작되면 `0.0.0.0:8000`에서 WebSocket 연결을 수신합니다. 이 터미널은 서버를 실행한 채로 유지합니다.

`-s` 옵션은 바인딩할 주소를 지정합니다. 기본값은 `0.0.0.0:8000`입니다.

## 2단계: Alice가 회의방 만들기

**새 터미널**을 열고 Alice가 회의방을 생성합니다:

```bash
uv run doorae create -u alice -s localhost:8000
```

| 옵션 | 설명 |
|------|------|
| `-u alice` | 서버에서 표시할 사용자 이름 |
| `-s localhost:8000` | 접속할 서버 주소 |

회의방이 생성되면 room ID가 표시됩니다. 이 ID를 다른 참가자에게 공유합니다.

추가 옵션으로 회의 시작 메시지(`-m`)나 커스텀 프로필(`-p`)을 지정할 수도 있습니다:

```bash
uv run doorae create -u alice -s localhost:8000 -m "긴급 버그 대응 회의"
```

## 3단계: Bob이 회의방에 참여하기

**또 다른 터미널**을 열고 Bob이 Alice가 만든 회의방에 참여합니다:

```bash
uv run doorae join <room_id> -u bob -s localhost:8000
```

`<room_id>`는 2단계에서 Alice가 방을 만들 때 생성된 ID입니다.

## 4단계: 회의방 목록 확인하기

누구든 서버의 전체 회의방 목록을 조회할 수 있습니다:

```bash
uv run doorae rooms -s localhost:8000
```

현재 활성화된 회의방들의 정보가 테이블로 출력됩니다.

## 전체 흐름 요약

```text
Alice 터미널               Doorae 서버                Bob 터미널
────────────               ───────────                ──────────
                           doorae serve
                           (8000 포트 수신 대기)
doorae create ──────────►  회의방 생성
(room_id 수신) ◄────────   room_id 반환
                                                      doorae join <room_id>
                           ◄──────────────────────────
WebSocket 연결 ◄──────────►  /ws/<room_id>  ◄──────────► WebSocket 연결
메시지 송수신  ◄──────────►  브로드캐스트   ◄──────────► 메시지 송수신
```

**동작 순서:**

1. 서버가 시작되면 REST API와 WebSocket 엔드포인트가 활성화됩니다.
2. `doorae create`는 `POST /api/rooms`로 회의방을 생성한 뒤, WebSocket(`/ws/<room_id>`)으로 연결합니다.
3. `doorae join`은 기존 방의 WebSocket에 바로 연결합니다.
4. 모든 참가자가 연결되면 워크플로우가 시작되고, AI 에이전트의 응답이 WebSocket을 통해 실시간으로 전달됩니다.
5. 사람 참가자의 입력도 WebSocket을 통해 전송되어 AI 에이전트가 참고합니다.

## 환경 변수로 서버 주소 설정하기

매번 `-s` 옵션을 입력하는 대신, 환경 변수로 설정할 수 있습니다:

```bash
export DOORAE_SERVER=localhost:8000

# 이후 -s 옵션 없이 사용 가능
uv run doorae create -u alice
uv run doorae join <room_id> -u bob
uv run doorae rooms
```

## 다음 단계

- [사람이 회의에 참여하기](human-participation.md) - 서버 모드에서 사람이 직접 발언하기
- [MCP Tool 연동](mcp-tool-integration.md) - 서버 모드에서도 GitHub 도구 활용하기
