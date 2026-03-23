# 트러블슈팅 가이드

Doorae 실행 중 자주 발생하는 문제와 해결 방법을 정리합니다.

---

## API Key 오류

### Main LLM API key is required

**문제**

```
ValueError: Main LLM API key is required.
Please set one of the following in your .env file:
  - LLM_MAIN_API_KEY (Main LLM 전용)
  - OPENAI_API_KEY (공통 fallback)
```

**원인**: Main LLM API 키가 설정되지 않았습니다.

**해결**: `.env` 파일에 다음 중 하나를 설정하세요:

```env
OPENAI_API_KEY=sk-xxxx
```

또는 프로바이더별 전용 키:

```env
LLM_MAIN_API_KEY=sk-xxxx
```

### Task LLM API key is required

**문제**: Task LLM 전용 키 오류 (위와 동일한 형식).

**해결**: `LLM_TASK_API_KEY` 또는 `OPENAI_API_KEY`를 설정하세요. 공통 `OPENAI_API_KEY`가 있으면 Main과 Task 모두 사용합니다.

### 에이전트별 API key 오류

**문제**: `agent_profiles.yaml`에서 `llm.api_key: "${MY_KEY}"` 설정 후 해당 환경변수가 미설정.

**원인**: `${MY_KEY}` 패턴이 환경변수에서 찾을 수 없으면 `None`이 되고, 글로벌 fallback도 없으면 에러 발생.

**해결**: 해당 환경변수를 `.env`에 추가하거나, `llm.api_key` 필드를 제거하여 글로벌 설정을 사용하세요.

---

## MCP 서버 초기화 실패

### MCP 도구를 사용할 수 없습니다

**문제**

```
⚠️  MCP 도구를 사용할 수 없습니다
   확인 사항:
   1. config/mcp_servers.json 파일 존재 여부
   2. .env 파일의 GITHUB_PERSONAL_ACCESS_TOKEN 설정 여부
```

**원인**: MCP 서버 설정 파일이 없거나, 필요한 인증 토큰이 설정되지 않았습니다.

**해결**:

1. `config/mcp_servers.json` 파일이 존재하는지 확인
2. 프로젝트 모드를 사용 중이라면 `.doorae/projects/<slug>/config/mcp_servers.json` 경로 확인
3. GitHub MCP를 사용하는 경우 `.env`에 설정:

```env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxx
```

### MCP 초기화 실패: {에러 메시지}

**문제**: MCP 서버 프로세스가 시작되지 않거나 연결 실패.

**원인**: MCP 서버 바이너리가 없거나, 네트워크 문제, 또는 설정 오류.

**해결**:

1. `--verbose` 플래그로 상세 로그 확인:
   ```bash
   doorae -v
   ```
2. `mcp_servers.json`의 command 경로가 올바른지 확인
3. MCP 없이도 회의는 진행 가능 — `mcp_tools` 필드를 제거하면 해당 에이전트는 tool 없이 대화만 수행

---

## 에이전트 관련 오류

### Duplicate top-level agent name detected

**문제**

```
ValueError: Duplicate top-level agent name detected: PM
```

**원인**: `agent_profiles.yaml`에 같은 이름의 최상위 에이전트가 두 번 정의되어 있습니다.

**해결**: 에이전트 이름을 고유하게 변경하세요.

### Duplicate agent name detected

**문제**

```
ValueError: Duplicate agent name detected: Backend
```

**원인**: 계층 전체에서 같은 이름이 중복됩니다 (예: 다른 supervisor 아래에 같은 이름의 sub-agent).

**해결**: 모든 레벨에서 에이전트 이름이 고유해야 합니다. `Backend1`, `Backend2` 등으로 구분하세요.

### Agent cycle detected

**문제**

```
ValueError: Agent cycle detected: A -> B -> A
```

**원인**: sub-agent가 자신의 상위 에이전트를 다시 참조하는 순환 구조.

**해결**: 계층 구조에서 순환 참조를 제거하세요.

---

## 무한루프 / 회의가 끝나지 않음

### 증상

에이전트들이 같은 주제를 반복하거나, Host가 종료를 선언하지 않습니다.

### 원인과 해결

**원인 1**: `MAX_TURNS`가 너무 높거나 기본값(1000) 그대로 사용.

**해결**: 적절한 턴 제한을 설정하세요:

```env
MAX_TURNS=100
```

**원인 2**: `RECURSION_LIMIT`에 도달.

**해결**: 제한값을 확인하고, 도달 시 LangGraph가 자동 종료합니다:

```env
RECURSION_LIMIT=500
```

**원인 3**: Host 에이전트가 종료 시그널을 발언하지 않음.

**해결**: `agent_profiles.yaml`에서 Host의 `metadata.additional_instructions`에 종료 프로토콜이 정의되어 있는지 확인하세요. 기본 템플릿에는 종료 조건과 종료 시그널 발언 규칙이 포함되어 있습니다.

**원인 4**: Host 체크인이 비활성화되어 진행 상황 점검이 없음.

**해결**:

```env
HOST_CHECKIN_INTERVAL=10    # 0이면 비활성화, 10이면 10턴마다 체크인
```

---

## WebSocket 연결 오류

### 서버 연결 시간이 초과되었습니다

**문제**: `doorae create` 또는 `doorae join` 실행 시 10초 내에 서버에 연결하지 못함.

**원인**: 서버가 실행되지 않았거나, 주소/포트가 잘못되었습니다.

**해결**:

1. 서버가 실행 중인지 확인:
   ```bash
   doorae serve
   ```
2. 서버 주소가 올바른지 확인 (기본: `localhost:8000`)
3. 방화벽이 해당 포트를 차단하지 않는지 확인

### 회의방을 찾을 수 없습니다

**문제**: WebSocket 연결 시 4004 코드로 닫힘.

**원인**: 존재하지 않는 room_id로 연결을 시도했습니다.

**해결**:

1. `doorae rooms -s localhost:8000`으로 현재 회의방 목록 확인
2. room_id를 정확히 복사하여 사용

### 서버 워크플로우 시작 실패

**문제**: 회의방에 입장했지만 AI 워크플로우가 시작되지 않음.

**원인**: 워크플로우 시작 조건 미충족 또는 API 오류.

**해결**:

- 409 Conflict: 이미 워크플로우가 실행 중. 정상 동작입니다.
- 400 Bad Request: 참가자가 없음. WebSocket 연결 후 다시 시도하세요.
- 500 Internal Error: 서버 로그 확인 (`doorae serve` 터미널 출력)

---

## 서버 의존성 오류

### Server mode requires optional dependencies

**문제**

```
Server mode requires optional dependencies. Run 'uv sync --extra server'.
```

**원인**: `fastapi`, `uvicorn` 등 서버 의존성이 설치되지 않았습니다.

**해결**:

```bash
uv sync --extra server
```

---

## TUI 관련 오류

### Terminal too small for TUI

**문제**

```
Terminal too small for TUI (60x20), falling back to CLI
```

**원인**: 터미널 크기가 80x24 미만.

**해결**: 터미널을 80x24 이상으로 확장하거나, `--classic` 플래그를 사용하세요.

### TUI가 자동 비활성화됨

**문제**: 파이프라인이나 비대화형 환경에서 TUI가 활성화되지 않음.

**원인**: stdout이 TTY가 아닙니다.

**해결**: 대화형 터미널에서 직접 실행하세요. 파이프라인에서는 `--classic`이 자동 적용됩니다.

---

## Workspace / Project 오류

### Workspace not found

**문제**

```
Workspace not found at /path/to/.doorae. Run 'doorae init' first.
```

**원인**: `doorae run`을 실행했지만 workspace가 초기화되지 않았습니다.

**해결**:

```bash
doorae init
```

### Workspace already exists

**문제**

```
Workspace already exists at /path/to/.doorae. Re-run with --force to rewrite workspace metadata.
```

**원인**: 이미 초기화된 workspace에서 `doorae init`을 재실행.

**해결**: 재초기화가 필요하면:

```bash
doorae init --force
```

### No current project is set

**문제**

```
No current project is set in /path/to/.doorae/workspace.yaml.
Use 'doorae run --project <slug|path>' or update current_project.
```

**원인**: workspace에 기본 프로젝트가 설정되지 않았습니다.

**해결**:

1. 프로젝트를 지정하여 실행:
   ```bash
   doorae run --project my-project
   ```
2. 또는 `.doorae/workspace.yaml`에서 `current_project` 설정:
   ```yaml
   current_project: my-project
   ```

### Project not found

**문제**

```
Project 'sprint-review' was not found at /path/to/.doorae/projects/sprint-review.
```

**원인**: 해당 slug의 프로젝트가 생성되지 않았습니다.

**해결**:

```bash
doorae project create "Sprint Review"
```

---

## 디버깅 팁

### verbose 모드 활용

```bash
doorae -v --classic
```

DEBUG 레벨 로깅이 활성화되어 LLM 호출, MCP tool 호출, 그래프 전이 등의 상세 정보를 확인할 수 있습니다. `--classic`을 함께 사용하면 TUI 없이 로그가 직접 출력됩니다.

### LangSmith 추적

LLM 호출의 프롬프트와 응답을 상세히 확인하려면:

```bash
doorae --trace -v
```

[LangSmith 추적 설정 가이드](langsmith-tracing.md)를 참고하세요.

### 커스텀 .env로 테스트

문제 재현 시 격리된 환경에서 테스트:

```bash
doorae -c test.env --classic -v
```
