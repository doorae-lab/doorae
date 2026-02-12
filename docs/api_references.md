# API Reference

> 전체 API 엔드포인트 목록. 각 기능별 상세 스펙은 `.specs/` 디렉토리의 개별 문서를 참고한다.

Base URL: `/api`

---

## 1. 인증 (Auth)

> 스펙: `.specs/user/106-유저-관리/113-회원가입로그인.md`, `133-회원가입로그인-화면.md`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `POST` | `/api/auth/register` | 회원가입 | #113, #133 |
| `POST` | `/api/auth/login` | 로그인 (JWT 발급) | #113, #133 |

---

## 2. 프로젝트 관리 (Project)

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

## 3. 에이전트 프로필 (Profile)

> 스펙: `.specs/agent/105-에이전트-기능/`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `GET` | `/api/profiles` | 에이전트 프로필 목록 조회 | #112, #114 |
| `GET` | `/api/profiles/{id}` | 에이전트 프로필 상세 조회 | #112, #114 |

---

## 4. 미팅 (Meeting)

> 스펙: `.specs/project/107-프로젝트-기능-미팅/`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `POST` | `/api/projects/{id}/meetings` | 미팅 생성 | #108 |
| `GET` | `/api/projects/{id}/meetings` | 미팅 목록 조회 | #107 |
| `GET` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 상세 조회 | #108 |
| `PATCH` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 수정 | #108 |
| `DELETE` | `/api/projects/{id}/meetings/{meeting_id}` | 미팅 취소 | #109 |

---

## 5. 안건 (Agenda)

> 스펙: `.specs/project/107-프로젝트-기능-미팅/110-미팅-안건-crud.md`

| 메서드 | 엔드포인트 | 설명 | 이슈 |
|--------|-----------|------|------|
| `GET` | `/api/agendas/templates` | 안건 템플릿 목록 (Optional) | #110 |
| `GET` | `/api/projects/{id}/meetings/{mid}/agendas` | 안건 목록 조회 | #110 |
| `POST` | `/api/projects/{id}/meetings/{mid}/agendas` | 안건 추가 | #110 |
| `PUT` | `/api/projects/{id}/meetings/{mid}/agendas/{aid}` | 안건 수정 | #110 |
| `DELETE` | `/api/projects/{id}/meetings/{mid}/agendas/{aid}` | 안건 삭제 | #110 |

---

## 6. WebSocket

> 스펙: `.specs/meeting/115-회의-시스템-기본-구현/`

### 접속

```
WS /ws/{room_id}?token={access_token}
```

### 이벤트

| 이벤트 | 방향 | 설명 |
|--------|------|------|
| `join` | Client → Server | 미팅 참가 |
| `chat.send` | Client → Server | 채팅 메시지 전송 |
| `meeting.control` | Client → Server | 미팅 제어 (시작/종료/일시중지) |
| `agent.stream` | Server → Client | 에이전트 응답 스트리밍 |
| `meeting.state` | Server → Client | 미팅 상태 변경 알림 |
| `agenda.updated` | Server → Client | 안건 상태 변경 알림 |
