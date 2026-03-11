# Doorae CLI workspace init

> Issue #205 범위: 현재 디렉터리에 Doorae workspace를 초기화하는 `doorae init` 명령을 정의한다.

## 목표

`doorae init`은 비어 있는 작업 디렉터리나 새 프로젝트 루트에서 바로 실행할 수 있어야 한다.

이 명령이 하는 일은 아래 네 가지다.

- `.doorae/` 디렉터리를 만든다.
- `.doorae/workspace.yaml`을 생성한다.
- `.doorae/projects/` 디렉터리를 준비한다.
- `.env`가 없으면 패키지에 포함된 `.env.example`을 복사해 `.env`를 만든다.

## 명령 계약

```bash
doorae init
doorae init --force
```

기본 동작:

- 현재 작업 디렉터리를 workspace 루트로 사용한다.
- 기존 `.env` 파일은 절대 덮어쓰지 않는다.
- 이미 workspace 메타데이터가 있으면 기본값으로 실패한다.
- `--force`를 주면 workspace 메타데이터만 다시 쓴다.

실패 조건:

- 이미 `.doorae/` 또는 `.doorae/workspace.yaml`이 존재하는데 `--force` 없이 다시 실행한 경우
- 패키지에 포함된 `.env.example`을 찾을 수 없는 경우
- 파일 시스템 권한 문제로 디렉터리 또는 파일을 만들 수 없는 경우

## 생성 결과

`doorae init` 후 작업 디렉터리는 아래 구조를 가진다.

```text
.doorae/
  workspace.yaml
  projects/
.env
```

`workspace.yaml` 내용:

```yaml
version: 1
current_project: null
projects_dir: .doorae/projects
```

## 재실행 규칙

### 이미 workspace가 있을 때

`doorae init`은 실패하고 `--force`를 다시 실행하라는 메시지를 출력한다.

### `--force`를 사용할 때

- `.doorae/workspace.yaml`은 현재 스키마로 다시 생성한다.
- `.doorae/projects/` 디렉터리는 유지한다.
- 기존 `.env` 파일은 그대로 둔다.

### `.env`가 이미 있을 때

- 새 템플릿을 복사하지 않는다.
- 사용자가 작성한 `.env` 내용을 그대로 유지한다.

## 예시 출력

첫 실행:

```text
Initialized Doorae workspace.
Workspace: <cwd>/.doorae
Projects: <cwd>/.doorae/projects
Created .env from the packaged template.
```

기존 `.env`가 있을 때:

```text
Initialized Doorae workspace.
Workspace: <cwd>/.doorae
Projects: <cwd>/.doorae/projects
Kept existing .env.
```

`--force` 재실행:

```text
Reinitialized Doorae workspace.
Workspace: <cwd>/.doorae
Projects: <cwd>/.doorae/projects
Kept existing .env.
```

## 검증 기준

아래 시나리오가 모두 통과하면 #205 범위를 충족한다.

- 빈 디렉터리에서 `doorae init`이 성공한다.
- 이미 workspace가 있을 때 `doorae init`은 실패한다.
- 같은 디렉터리에서 `doorae init --force`는 성공한다.
- `.env`가 없을 때만 `.env.example` 복사가 일어난다.
- README와 이 문서의 생성 결과 설명이 실제 출력과 일치한다.

## 후속 범위

이번 이슈는 workspace init까지만 다룬다.

아래 항목은 별도 이슈로 분리한다.

- `doorae project create`
- current project 선택 및 저장
- project-aware `doorae run`
- 프로젝트 템플릿과 MCP 서버별 초기화
