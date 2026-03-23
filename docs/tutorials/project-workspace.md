# 프로젝트 워크스페이스

이 튜토리얼에서는 `doorae init`으로 워크스페이스를 초기화하고, `doorae project create`로 프로젝트를 생성한 뒤, 프로젝트 기반으로 회의를 실행합니다.

## 사전 준비

- Doorae 클론 및 의존성 설치 완료
- `.env`에 API key가 설정된 상태 (아직 없어도 `init`에서 템플릿이 생성됨)

## 1단계: 워크스페이스 초기화하기

Doorae 프로젝트 루트에서 다음 명령을 실행합니다:

```bash
uv run doorae init
```

성공하면 다음과 같은 출력을 볼 수 있습니다:

```
Initialized Doorae workspace.
Workspace: /home/user/doorae/.doorae
Projects: /home/user/doorae/.doorae/projects
Created .env from the packaged template.
```

이 명령은 다음을 수행합니다:

| 생성 항목 | 경로 | 설명 |
|-----------|------|------|
| 워크스페이스 디렉터리 | `.doorae/` | 워크스페이스 메타데이터 저장소 |
| 워크스페이스 설정 | `.doorae/workspace.yaml` | 버전, 현재 프로젝트, 프로젝트 경로 설정 |
| 프로젝트 디렉터리 | `.doorae/projects/` | 개별 프로젝트 scaffold 저장소 |
| 환경 변수 파일 | `.env` | LLM API key 등 설정 (기존 `.env`가 있으면 건너뜀) |

`.doorae/workspace.yaml`의 내용은 다음과 같습니다:

```yaml
version: 1
current_project: null
projects_dir: .doorae/projects
```

## 2단계: 프로젝트 생성하기

워크스페이스 안에 "demo"라는 프로젝트를 생성합니다:

```bash
uv run doorae project create demo
```

출력:

```
Created Doorae project.
Project: /home/user/doorae/.doorae/projects/demo
Slug: demo
```

## 3단계: 생성된 파일 확인하기

프로젝트 scaffold는 다음 파일들로 구성됩니다:

```
.doorae/projects/demo/
├── project.yaml                  # 프로젝트 메타데이터
└── config/
    ├── agent_profiles.yaml       # 에이전트 프로필 정의
    ├── agendas.yaml              # 회의 안건 목록
    └── mcp_servers.json          # MCP 서버 설정
```

`project.yaml`의 내용:

```yaml
version: 1
name: demo
slug: demo
agent_profiles_path: config/agent_profiles.yaml
agendas_path: config/agendas.yaml
mcp_servers_path: config/mcp_servers.json
```

각 config 파일의 경로는 `project.yaml` 기준 상대 경로로 해석됩니다. 원한다면 절대 경로나 프로젝트 외부 경로를 지정할 수도 있습니다.

## 4단계: .env 설정하기

프로젝트 루트의 `.env` 파일을 열고 API key를 설정합니다:

```env
# 공통 설정 (Fallback)
OPENAI_API_KEY=your-api-key-here

# OpenRouter 사용 시 (권장)
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Main LLM (회의 에이전트 응답 생성)
LLM_MAIN_MODEL=qwen/qwen3.5-flash-02-23

# Task LLM (멘션 추출, 종료 감지, 안건 분석)
LLM_TASK_MODEL=google/gemini-2.5-flash
```

상세한 LLM provider 설정은 [LLM Provider 설정](llm-provider-setup.md) 튜토리얼을 참고하세요.

## 5단계: 프로젝트 기반 회의 실행하기

```bash
uv run doorae run --project demo
```

이 명령은 `.doorae/projects/demo/` 안의 설정 파일들을 사용하여 회의를 시작합니다.

회의가 시작되면 안건 진행 상태 패널과 함께 에이전트들의 대화가 표시됩니다:

```
┌──────────────── 📋 안건 진행 상태 ────────────────┐
│  🔄 1. 프로젝트 로드맵 논의 (Host) [0:30] ← 현재  │
│  ⏳ 2. 프로젝트 달성 계획 (Host)                   │
│  ⏳ 3. 스프린트 리뷰 (PM)                          │
│  ⏳ 4. 스프린트 계획 (PM)                          │
└───────────────────────────────────────────────────┘

[Host]
안녕하세요, 오늘 회의를 시작하겠습니다...
```

## 추가 옵션

### Classic CLI 모드

TUI 대신 일반 텍스트 출력을 사용하려면:

```bash
uv run doorae run --project demo --classic
```

### 커스텀 .env 파일 지정

프로젝트별로 다른 `.env`를 사용하려면:

```bash
uv run doorae run --project demo --config .env.prod
```

### 커스텀 시작 메시지

```bash
uv run doorae run --project demo -m "긴급 버그 대응 회의를 시작합니다"
```

### 워크스페이스 재초기화

기존 워크스페이스 메타데이터를 덮어쓰려면 `--force` 옵션을 사용합니다:

```bash
uv run doorae init --force
```

## 프로젝트 이름 규칙

`doorae project create`에 전달하는 이름은 자동으로 slug로 변환됩니다:

| 입력 이름 | 변환된 slug |
|-----------|-------------|
| `demo` | `demo` |
| `My Project` | `my-project` |
| `sprint_review` | `sprint-review` |
| `프로젝트 1` | `프로젝트-1` |

slug는 프로젝트 디렉터리 이름으로 사용됩니다. 최소 하나의 글자나 숫자를 포함해야 합니다.

## 다음 단계

- [LLM Provider 설정](llm-provider-setup.md) - 다양한 LLM provider 구성하기
- [안건(Agenda) 설정](configure-agendas.md) - 회의 안건 커스터마이징
- [커스텀 에이전트 프로필](custom-agent-profiles.md) - 에이전트 추가 및 역할 정의
