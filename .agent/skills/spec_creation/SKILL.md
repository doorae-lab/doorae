---
name: spec-creation
description: Use when creating or organizing .specs files - ensures consistent directory structure, metadata templates, and bidirectional references between parent and child specs
---

# Spec Creation Skill

`.specs/` 디렉토리에 스펙 파일을 일관된 형식으로 생성한다. 이슈번호/Epic번호 없이 도메인과 주제 기반으로 구성한다.

## Directory Structure

```
.specs/{도메인}/{상위스펙명}/{하위스펙명}.md
```

- 도메인: `agent`, `infra`, `interface`, `meeting`, `project`, `user` 등
- 이름: 한글 케밥(kebab) 표기 (예: `회의-시스템-기본-구현`)

## 상위 스펙 규칙

각 디렉토리에는 반드시 하나의 상위 스펙이 존재한다:
- **명시적 상위 스펙**: 디렉토리와 같은 이름의 파일 (예: `서버-인터페이스/서버-인터페이스.md`)
- **기본 상위 스펙**: 특별한 상위 문서가 없으면 `__init__.md`를 상위 문서로 사용

## Templates

### 상위 스펙 (명시적 또는 `__init__.md`)

```markdown
# {제목}

- 상태: draft
- 작성일: {YYYY-MM-DD}

## 개요
{설명}

## 하위 스펙
- [{하위스펙명}](./{하위스펙명}.md) - 한줄 요약
```

### 하위 스펙

```markdown
# {제목}

- 상위: [{상위스펙명}](./{상위파일명}.md) - 한줄 요약
- 상태: draft
- 작성일: {YYYY-MM-DD}

## 개요
{설명}

## 관련 코드
- `{파일경로}`
```

## Metadata Rules

| 필드 | 값 | 비고 |
|------|-----|------|
| 상태 | `draft` \| `open` \| `done` | 기본값: `draft` |
| 작성일 | `YYYY-MM-DD` | 생성 시점 기준 |
| 상위 | 링크 + 한줄 요약 | 하위 스펙에만 |

## Bidirectional References

상위와 하위 스펙은 반드시 양방향 참조를 유지한다:

- **하위 -> 상위**: `- 상위: [{상위스펙명}](링크) - 한줄 요약`
- **상위 -> 하위**: `- [{하위스펙명}](링크) - 한줄 요약` (하위 스펙 섹션에 추가)

## Workflow

### Step 1: 정보 수집
사용자에게 확인:
- 도메인 (agent, infra, interface, meeting, project, user 등)
- 스펙 제목
- 상위 스펙 여부 (독립/상위/하위)
- 하위 스펙이면 상위 스펙 경로

### Step 2: 디렉토리 확인/생성
- `.specs/{도메인}/{상위스펙명}/` 디렉토리 존재 확인
- 없으면 생성

### Step 3: 템플릿 기반 파일 생성
- 해당 유형(독립/상위/하위)의 템플릿 적용
- 상태 기본값: `draft`
- 작성일: 현재 날짜

### Step 4: 양방향 참조 설정
- 하위 스펙 생성 시 상위 스펙의 `하위 스펙` 섹션에 링크 추가
- 상위 스펙 생성 시 기존 하위 스펙이 있으면 참조 확인

### Step 5: 검증
- 같은 디렉토리에 동일 이름 파일 중복 확인
- 네이밍 컨벤션 준수 확인 (한글 케밥 표기)

## Common Mistakes

| 실수 | 올바른 방법 |
|------|------------|
| 이슈번호를 파일명에 포함 | 주제 기반 이름만 사용 |
| 양방향 참조 누락 | 하위 생성 시 상위도 반드시 수정 |
| 상태 필드 누락 | 항상 `draft`로 시작 |
| 상위 링크에 한줄 요약 누락 | `[이름](링크) - 한줄 요약` 형식 준수 |
| 디렉토리에 상위 스펙 없음 | 명시적 이름이 없으면 `__init__.md` 생성 |
