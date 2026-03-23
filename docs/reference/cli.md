# CLI Reference

소스: `doorae/interfaces/cli.py`

Doorae CLI는 [Typer](https://typer.tiangolo.com/) 기반이다. 엔트리포인트는 `doorae` 이며, `doorae/__main__.py`를 통해 `python -m doorae`로도 실행 가능하다.

## 전역 옵션 (callback)

서브커맨드 없이 `doorae`를 실행하면 로컬 회의가 시작된다.

```
doorae [OPTIONS]
```

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `--message` | `-m` | `str` | `"회의를 시작합니다"` | 회의 시작 메시지 |
| `--profiles` | `-p` | `Path` | `None` | Agent 프로필 YAML 파일 경로. 파일이 존재해야 한다. |
| `--classic` | | `bool` | `False` | TUI 대신 클래식 CLI 출력 사용 |
| `--config` | `-c` | `Path` | `None` | `.env` 설정 파일 경로. 파일이 존재해야 한다. |
| `--verbose` | `-v` | `bool` | `False` | 상세 출력 (DEBUG 레벨) |
| `--quiet` | `-q` | `bool` | `False` | 최소 출력 (WARNING 레벨만) |
| `--version` | `-V` | `bool` | `False` | 버전 정보 출력 후 종료 |
| `--trace` | `-t` | `bool` | `None` | LangSmith 추적 활성화. `None`이면 `LANGCHAIN_TRACING_V2` 환경 변수를 따른다. |
| `--hide-delegated` | | `bool` | `False` | 서브 에이전트(위임) 발언 숨김 (CLI classic 모드) |

TUI 사용 조건: `--classic`이 `False`이고, stdout이 TTY이며, 터미널 크기가 80x24 이상일 때 TUI가 활성화된다.

## run

```
doorae run [OPTIONS]
```

Workspace project를 사용하여 회의를 실행한다. `.doorae/workspace.yaml`의 `current_project` 또는 `--project` 옵션으로 지정한 프로젝트의 설정 파일을 사용한다.

| 옵션 | 단축 | 타입 | 기본값 | 설명 |
|------|------|------|--------|------|
| `--project` | | `str` | `None` | Workspace project slug 또는 project 경로 |
| `--message` | `-m` | `str` | `"회의를 시작합니다"` | Meeting start message |
| `--classic` | | `bool` | `False` | Use classic CLI output instead of TUI |
| `--config` | `-c` | `Path` | `None` | Path to a custom .env file |
| `--verbose` | `-v` | `bool` | `False` | Enable verbose logging |
| `--quiet` | `-q` | `bool` | `False` | Reduce logging output |
| `--trace` | `-t` | `bool` | `None` | Enable LangSmith tracing |
| `--hide-delegated` | | `bool` | `False` | Hide delegated sub-agent output in classic CLI mode |

## init

```
doorae init [OPTIONS]
```

현재 디렉터리에 `.doorae` 워크스페이스를 초기화한다. `.doorae/workspace.yaml`과 `.doorae/projects/` 디렉터리를 생성하고, `.env` 파일이 없으면 패키지 내장 템플릿에서 복사한다.

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--force` | `bool` | `False` | 기존 워크스페이스 메타데이터가 있으면 덮어쓴다 |

## project create

```
doorae project create NAME
```

현재 워크스페이스 안에 scaffolded project를 생성한다. `.doorae/projects/<slug>/` 아래에 `project.yaml`, `config/agent_profiles.yaml`, `config/agendas.yaml`, `config/mcp_servers.json`이 생성된다.

| 인자 | 타입 | 설명 |
|------|------|------|
| `NAME` | `str` (필수) | 프로젝트 이름. 자동으로 slug로 변환된다. |

slug 변환 규칙: NFKC 정규화 후 소문자로 변환하고, 공백과 `_`를 `-`로 치환하며, 영숫자와 `-` 이외의 문자를 제거한다.

## serve

```
doorae serve [OPTIONS]
```

Doorae WebSocket 서버를 시작한다. FastAPI + Uvicorn 기반이며, `uv sync --extra server`로 의존성 설치가 필요하다.

| 옵션 | 단축 | 타입 | 기본값 | 환경 변수 | 설명 |
|------|------|------|--------|-----------|------|
| `--server` | `-s` | `str` | `"0.0.0.0:8000"` | `DOORAE_SERVER` | 바인딩할 서버 주소 |

## create

```
doorae create [OPTIONS]
```

서버에 새 회의방을 만들고 TUI 클라이언트로 바로 입장한다.

| 옵션 | 단축 | 타입 | 기본값 | 환경 변수 | 설명 |
|------|------|------|--------|-----------|------|
| `--username` | `-u` | `str` | `"user"` | | 서버에서 표시할 사용자 이름 |
| `--server` | `-s` | `str` | `None` (필수) | `DOORAE_SERVER` | 접속할 서버 주소 (예: `localhost:8000`) |
| `--message` | `-m` | `str` | `"회의를 시작합니다"` | | 회의 시작 메시지 |
| `--profiles` | `-p` | `Path` | `None` | | Agent 프로필 YAML 파일 경로 |

## join

```
doorae join ROOM_ID [OPTIONS]
```

기존 회의방에 TUI 클라이언트로 입장한다.

| 인자 | 타입 | 설명 |
|------|------|------|
| `ROOM_ID` | `str` (필수) | 입장할 회의방 ID |

| 옵션 | 단축 | 타입 | 기본값 | 환경 변수 | 설명 |
|------|------|------|--------|-----------|------|
| `--username` | `-u` | `str` | `"user"` | | 서버에서 표시할 사용자 이름 |
| `--server` | `-s` | `str` | `None` (필수) | `DOORAE_SERVER` | 접속할 서버 주소 (예: `localhost:8000`) |

## rooms

```
doorae rooms [OPTIONS]
```

서버의 회의방 목록을 조회하여 테이블로 출력한다.

| 옵션 | 단축 | 타입 | 기본값 | 환경 변수 | 설명 |
|------|------|------|--------|-----------|------|
| `--server` | `-s` | `str` | `None` (필수) | `DOORAE_SERVER` | 조회할 서버 주소 (예: `localhost:8000`) |

## 서버 주소 형식

`--server` 옵션과 `DOORAE_SERVER` 환경 변수는 다음 형식을 지원한다.

| 형식 | 예시 |
|------|------|
| `host:port` | `localhost:8000` |
| `ws://host:port` | `ws://localhost:8000` |
| `wss://host:port` | `wss://example.com:443` |
| `http://host:port` | `http://localhost:8000` |
| `https://host:port/path` | `https://example.com/doorae` |

`host:port` 형식으로 입력하면 HTTP는 `http://`, WebSocket은 `ws://`로 자동 변환된다. `https` 또는 `wss` scheme을 사용하면 양쪽 모두 TLS로 연결한다.
