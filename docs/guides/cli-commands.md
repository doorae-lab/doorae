# CLI 명령어 가이드

Doorae CLI는 `typer` 기반으로, 회의 실행부터 서버 관리까지 모든 작업을 커맨드라인에서 수행합니다.

---

## 기본 명령어 (doorae)

서브커맨드 없이 실행하면 바로 회의를 시작합니다.

```bash
doorae
```

### 주요 옵션

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--message` | `-m` | 회의 시작 메시지 | `"회의를 시작합니다"` |
| `--profiles` | `-p` | agent_profiles.yaml 경로 | `config/agent_profiles.yaml` |
| `--classic` | | TUI 대신 클래식 텍스트 출력 사용 | `false` |
| `--config` | `-c` | 커스텀 .env 파일 경로 | `.env` |
| `--verbose` | `-v` | DEBUG 레벨 로깅 활성화 | `false` |
| `--quiet` | `-q` | WARNING 레벨만 출력 | `false` |
| `--trace` | `-t` | LangSmith 추적 활성화 | `.env` 설정값 |
| `--version` | `-V` | 버전 정보 출력 | |
| `--hide-delegated` | | 위임된 sub-agent 발언 숨김 (classic 모드) | `false` |

### 실전 예제

커스텀 프로필로 회의 시작:

```bash
doorae -p my_team/agent_profiles.yaml -m "스프린트 리뷰를 시작합니다"
```

디버깅 모드 + LangSmith 추적:

```bash
doorae -v --trace -m "아키텍처 논의를 시작합니다"
```

파이프라인에서 사용 (TUI 자동 비활성화):

```bash
echo "결과 확인" | doorae --classic 2>&1 | tee meeting_log.txt
```

터미널이 80x24 미만이면 자동으로 classic 모드로 전환됩니다.

---

## doorae run

workspace project 기반으로 회의를 실행합니다. `doorae init`과 `doorae project create`로 구성한 프로젝트를 사용합니다.

```bash
doorae run
doorae run --project my-project
doorae run --project ./path/to/project
```

| 옵션 | 단축 | 설명 |
|------|------|------|
| `--project` | | workspace project slug 또는 프로젝트 경로 |
| `--message` | `-m` | 회의 시작 메시지 |
| `--classic` | | 클래식 CLI 출력 모드 |
| `--config` | `-c` | 커스텀 .env 경로 |
| `--verbose` | `-v` | 상세 로깅 |
| `--quiet` | `-q` | 최소 로깅 |
| `--trace` | `-t` | LangSmith 추적 |
| `--hide-delegated` | | 위임 발언 숨김 |

### 실전 예제

workspace의 current_project로 실행:

```bash
doorae run
```

특정 프로젝트 지정:

```bash
doorae run --project sprint-review
```

외부 경로의 프로젝트 실행:

```bash
doorae run --project ~/teams/backend/sprint-23
```

---

## doorae init

현재 디렉터리에 `.doorae` workspace를 초기화합니다. `.doorae/workspace.yaml`과 `.doorae/projects/` 디렉터리를 생성합니다.

```bash
doorae init
```

`.env` 파일이 없으면 패키지에 포함된 템플릿에서 자동 생성합니다.

이미 workspace가 존재할 때 재초기화:

```bash
doorae init --force
```

---

## doorae project create

workspace 안에 새 프로젝트 scaffold를 생성합니다. `config/agent_profiles.yaml`, `config/agendas.yaml`, `config/mcp_servers.json`이 기본 템플릿에서 복사됩니다.

```bash
doorae project create "Sprint Review"
```

결과:

```
Created Doorae project.
Project: /path/to/.doorae/projects/sprint-review
Slug: sprint-review
```

프로젝트 이름은 자동으로 slug로 변환됩니다 (공백 → 하이픈, 소문자화).

---

## doorae serve

FastAPI 기반 WebSocket 서버를 시작합니다.

```bash
doorae serve
doorae serve -s 0.0.0.0:9000
```

| 옵션 | 단축 | 환경변수 | 설명 | 기본값 |
|------|------|----------|------|--------|
| `--server` | `-s` | `DOORAE_SERVER` | 바인딩 주소 | `0.0.0.0:8000` |

서버 의존성이 필요합니다:

```bash
uv sync --extra server
```

의존성이 없으면 `Server mode requires optional dependencies` 오류가 발생합니다.

---

## doorae create

서버에 새 회의방을 만들고 TUI로 바로 입장합니다.

```bash
doorae create -s localhost:8000
doorae create -s localhost:8000 -u alice -m "백엔드 설계 회의"
```

| 옵션 | 단축 | 환경변수 | 설명 | 기본값 |
|------|------|----------|------|--------|
| `--server` | `-s` | `DOORAE_SERVER` | 서버 주소 | (필수) |
| `--username` | `-u` | | 표시 이름 | `user` |
| `--message` | `-m` | | 회의 시작 메시지 | `"회의를 시작합니다"` |
| `--profiles` | `-p` | | agent_profiles.yaml 경로 | `None` |

`DOORAE_SERVER` 환경변수를 설정해두면 `-s` 플래그를 생략할 수 있습니다:

```bash
export DOORAE_SERVER=localhost:8000
doorae create -u alice
```

---

## doorae join

기존 회의방에 입장합니다.

```bash
doorae join <ROOM_ID> -s localhost:8000 -u bob
```

| 인자/옵션 | 설명 |
|-----------|------|
| `ROOM_ID` | 입장할 회의방 ID (필수) |
| `--server` / `-s` | 서버 주소 |
| `--username` / `-u` | 표시 이름 (기본: `user`) |

회의방 생성자가 `doorae create` 실행 후 TUI에 표시되는 초대 명령어를 공유하면 됩니다:

```
doorae join abc-123-def -s localhost:8000 -u <name>
```

---

## doorae rooms

서버의 회의방 목록을 조회합니다.

```bash
doorae rooms -s localhost:8000
```

| 옵션 | 단축 | 환경변수 | 설명 |
|------|------|----------|------|
| `--server` | `-s` | `DOORAE_SERVER` | 조회할 서버 주소 |

---

## 자주 쓰는 워크플로우

### 로컬 1인 회의

```bash
doorae -m "이번 스프린트 회고를 시작합니다"
```

### 팀 회의 (서버 모드)

터미널 1 — 서버 시작:

```bash
doorae serve
```

터미널 2 — 회의방 생성 + 입장:

```bash
doorae create -s localhost:8000 -u alice -m "주간 회의를 시작합니다"
```

터미널 3 — 동료 입장:

```bash
doorae join <ROOM_ID> -s localhost:8000 -u bob
```

### 프로젝트 기반 워크플로우

```bash
doorae init
doorae project create "weekly-standup"
# .doorae/projects/weekly-standup/config/ 파일을 편집
doorae run --project weekly-standup
```

### 디버깅 + 추적

```bash
doorae -v --trace --classic -m "문제 상황 재현"
```

`--classic`을 함께 사용하면 TUI 없이 로그가 터미널에 직접 출력되어 디버깅이 용이합니다.
