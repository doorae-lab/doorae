# 미팅 안건 CRUD

- 이슈: #110
- Epic: #107 프로젝트 기능
- 상태: draft
- 작성일: 2026-02-10

## 개요

미팅의 안건(Agenda)을 생성, 조회, 수정, 삭제하는 기능.

## 요구사항

- [ ] 안건 목록 조회
- [ ] 안건 추가
- [ ] 안건 수정 (제목, 시간 제한, 필수 발언자)
- [ ] 안건 삭제
- [ ] 안건 순서 변경

## 인터페이스

### REST API

#### 안건 목록 조회

```
GET /api/projects/{id}/meetings/{mid}/agendas
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "agenda-001",
      "title": "현황 공유",
      "time_limit": 300,
      "required_speakers": ["Host", "PM"],
      "order": 1,
      "status": "pending"
    },
    {
      "id": "agenda-002",
      "title": "이슈 논의",
      "time_limit": 600,
      "required_speakers": ["TechLead"],
      "order": 2,
      "status": "pending"
    }
  ]
}
```

#### 안건 추가

```
POST /api/projects/{id}/meetings/{mid}/agendas
```

**Request Body:**

```json
{
  "title": "새로운 안건",
  "time_limit": 300,
  "required_speakers": ["PM"]
}
```

**Response (201 Created):**

```json
{
  "id": "agenda-003",
  "title": "새로운 안건",
  "time_limit": 300,
  "required_speakers": ["PM"],
  "order": 3,
  "status": "pending"
}
```

#### 안건 수정

```
PUT /api/projects/{id}/meetings/{mid}/agendas/{aid}
```

**Request Body:**

```json
{
  "title": "수정된 안건",
  "time_limit": 600,
  "required_speakers": ["PM", "TechLead"]
}
```

#### 안건 삭제

```
DELETE /api/projects/{id}/meetings/{mid}/agendas/{aid}
```

**Response (204 No Content)**

#### 안건 템플릿 조회 (Optional)

```
GET /api/agendas/templates
```

**Response (200 OK):**

```json
{
  "templates": [
    { "name": "주간 회의", "agendas": [...] },
    { "name": "브레인스토밍", "agendas": [...] }
  ]
}
```

## 관련 코드

- `doorae/core/agenda.py`
- `doorae/graph/nodes/process.py`
