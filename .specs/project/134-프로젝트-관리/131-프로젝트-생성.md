# 프로젝트 관리 (Web/API)

- 이슈: #131
- Epic: #134 프로젝트 관리
- 상태: draft
- 작성일: 2026-02-10

## 개요

프로젝트(미팅 그룹)를 생성하고 조회하는 관리 기능 (Web/API). CLI 기능은 별도 이슈(#135)로 분리됨.

## 스키마

### Project (프로젝트)

```python
class Project(BaseModel):
    """프로젝트 — 미팅을 묶는 상위 단위"""
    id: str                          # UUID
    name: str                        # 프로젝트 이름
    description: str = ""            # 프로젝트 설명
    owner_id: str                    # 생성자 (User ID)
    created_at: datetime
    updated_at: datetime

    # 에이전트 설정
    agent_profile_path: str          # agent_profiles.yaml 경로
    agents: List[AgentConfig] = []   # 참여 에이전트 목록

    # 미팅 기본값
    default_agendas: List[Agenda] = []       # 기본 안건 템플릿
    default_max_turns: int = 1000
    default_time_limit: int = 300            # 안건당 기본 시간(초)

    # LLM 설정
    main_model: Optional[str] = None         # None이면 글로벌 설정 사용
    task_model: Optional[str] = None

    # MCP 설정
    mcp_servers: List[str] = []              # 활성화할 MCP 서버 이름

    # 상태
    status: str = "active"                   # active, archived
```

### AgentConfig (에이전트 설정)

```python
class AgentConfig(BaseModel):
    """프로젝트 내 에이전트 설정"""
    profile_key: str               # agent_profiles.yaml 키 (Host, PM 등)
    is_active: bool = True         # 이 프로젝트에서 활성화 여부
    custom_instructions: str = ""  # 프로젝트별 추가 지시사항
    mcp_tools: List[str] = []     # 프로젝트별 MCP 도구 오버라이드
```

## 요구사항

- [ ] Project 모델 정의
- [ ] AgentConfig 모델 정의
- [ ] 프로젝트 생성 API
- [ ] **프로젝트 목록 조회 API**
- [ ] agent_profiles.yaml 경로 검증
- [ ] 기본값 적용 로직 (미팅 생성 시 project 설정 상속)
- [ ] **Frontend**: 프로젝트 목록 화면 구현
- [ ] **Frontend**: 프로젝트 생성 마법사 (Wizard) 구현
  - [ ] 기본 정보 입력 (Step 1)
  - [ ] 에이전트 설정 (Step 2)
  - [ ] 안건 설정 (Step 3)

## 인터페이스

### REST API

```
POST /api/projects
```

**Request Body:**

```json
{
  "name": "주간 개발 회의",
  "description": "매주 월요일 개발팀 정기 회의",
  "agent_profile_path": "config/agent_profiles.yaml",
  "agents": [
    { "profile_key": "Host", "is_active": true },
    { "profile_key": "PM", "is_active": true },
    { "profile_key": "TechLead", "is_active": true, "custom_instructions": "코드 리뷰 중심 피드백" }
  ],
  "default_agendas": [
    { "title": "현황 공유", "required_speakers": ["Host", "PM"] },
    { "title": "이슈 논의", "required_speakers": ["TechLead"] }
  ],
  "main_model": null,
  "task_model": null,
  "mcp_servers": ["github"]
}
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "주간 개발 회의",
  "description": "매주 월요일 개발팀 정기 회의",
  "owner_id": "user-123",
  "status": "active",
  "agents": [...],
  "default_agendas": [...],
  "created_at": "2026-02-10T21:00:00Z",
  "updated_at": "2026-02-10T21:00:00Z"
}
```

**에러 응답:**

| 코드 | 상황 |
|---|---|
| `400` | name 누락, agent_profile_path 유효하지 않음 |
@ -120,6 +120,38 @@
 | `401` | 인증 실패 |
 | `409` | 동일 이름 프로젝트 존재 |
 
### REST API - 목록 조회

```
GET /api/projects
```

**Query Parameters:**
- `page`: 페이지 번호 (default: 1)
- `limit`: 페이지 당 개수 (default: 20)
- `status`: 상태 필터 (active, archived)

**Response (200 OK):**

```json
{
  "total": 12,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "주간 개발 회의",
      "description": "매주 월요일 개발팀 정기 회의",
      "owner_id": "user-123",
      "status": "active",
      "agent_count": 3,
      "created_at": "2026-02-10T21:00:00Z"
    },
    ...
  ]
}
```

### REST API - 상세 조회

```
GET /api/projects/{id}
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "주간 개발 회의",
  "description": "매주 월요일 개발팀 정기 회의",
  "owner_id": "user-123",
  "status": "active",
  "agents": [...],
  "default_agendas": [...],
  "main_model": null,
  "task_model": null,
  "mcp_servers": ["github"],
  "created_at": "2026-02-10T21:00:00Z",
  "updated_at": "2026-02-10T21:00:00Z"
}
```

### REST API - 프로젝트 수정

```
PATCH /api/projects/{id}
```

**Request Body (부분 업데이트):**

```json
{
  "name": "수정된 프로젝트 이름",
  "description": "수정된 설명",
  "status": "archived"
}
```

**Response (200 OK):** 수정된 Project 객체

**에러 응답:**

| 코드 | 상황 |
|------|------|
| `400` | 유효하지 않은 필드 |
| `401` | 인증 실패 |
| `404` | 프로젝트가 존재하지 않음 |

### REST API - 프로젝트 삭제

```
DELETE /api/projects/{id}
```

**Response (204 No Content)**

**에러 응답:**

| 코드 | 상황 |
|------|------|
| `401` | 인증 실패 |
| `404` | 프로젝트가 존재하지 않음 |

### Frontend (Web UI)
 
 **프로젝트 생성 마법사 (Wizard)**

*   **Step 1: 기본 정보**
    - [ ] 프로젝트 이름 (필수)
    - [ ] 설명 (선택)
    - [ ] 템플릿 선택 (빈 프로젝트, 주간 회의, 브레인스토밍 등)

*   **Step 2: 에이전트 설정**
    - [ ] **에이전트 목록**: 시스템에 등록된 에이전트(Host, PM, etc.) 목록 표시.
    - [ ] **활성화 토글**: 각 에이전트의 참여 여부 선택.
    - [ ] **상세 설정**: 에이전트 클릭 시 '추가 지시사항(Custom Instructions)' 입력 필드 노출.
    - [ ] **MCP 도구 선택**: 각 에이전트가 사용할 도구 오버라이드 설정 (고급).

*   **Step 3: 안건(Agenda) 설정**
    - [ ] **기본 안건 목록**: 템플릿에 따른 초기 안건 표시.
    - [ ] **안건 추가/수정/삭제**: 제목, 필수 발언자, 시간 제한 설정.
    - [ ] **Drag & Drop**: 안건 순서 변경.

*   **Step 4: 검토 및 생성**
    - [ ] 전체 설정 요약 표시.
    - [ ] **'프로젝트 생성' 버튼**: 클릭 시 API 호출 (`POST /api/projects`).

