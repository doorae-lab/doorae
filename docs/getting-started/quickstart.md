# 빠른 시작

이 튜토리얼에서는 워크스페이스를 초기화하고, 프로젝트를 생성하고, 환경을 설정한 뒤 첫 회의를 실행하는 과정을 안내합니다.

!!! note "사전 준비"
    [설치](installation.md)를 완료한 상태에서 진행하세요.

## 1단계: 워크스페이스 초기화

`doorae init`은 현재 디렉터리에 `.doorae/` 워크스페이스 디렉터리와 `.env` 파일을 생성합니다.

```bash
uv run doorae init
```

**예상 출력:**

```
Initialized Doorae workspace.
Workspace: /path/to/doorae/.doorae
Projects: /path/to/doorae/.doorae/projects
Created .env from the packaged template.
```

!!! info "생성되는 항목"
    - `.doorae/workspace.yaml` -- 워크스페이스 메타데이터
    - `.doorae/projects/` -- 프로젝트 스캐폴드가 저장되는 디렉터리
    - `.env` -- 환경 변수 설정 파일 (기존 `.env`가 없는 경우에만 생성)

## 2단계: 프로젝트 생성

`doorae project create`는 프로젝트별 에이전트 프로필, 안건, MCP 설정을 스캐폴딩합니다.

```bash
uv run doorae project create demo
```

**예상 출력:**

```
Created Doorae project.
Project: /path/to/doorae/.doorae/projects/demo
Slug: demo
```

이 명령어는 `.doorae/projects/demo/` 아래에 다음 파일들을 생성합니다.

```
.doorae/projects/demo/
├── project.yaml                  # 프로젝트 메타데이터
└── config/
    ├── agent_profiles.yaml       # 에이전트(참여자) 프로필
    ├── agendas.yaml              # 회의 안건 목록
    └── mcp_servers.json          # MCP 도구 서버 설정
```

기본 프로필에는 **Host** (회의 진행자), **PM** (프로젝트 매니저), **TechLead** (기술 리더)가 포함되어 있으며, TechLead의 하위 에이전트로 **Backend**와 **Frontend**가 설정되어 있습니다.

## 3단계: 환경 변수 설정

`.env` 파일을 열어 API 키와 모델을 설정합니다.

### OpenRouter 사용 (권장)

```env
# API 키
OPENAI_API_KEY=your-api-key-here

# OpenRouter 엔드포인트
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Main LLM (회의 에이전트 응답 생성)
LLM_MAIN_MODEL=qwen/qwen3.5-flash-02-23

# Task LLM (멘션 추출, 종료 감지, 안건 분석)
LLM_TASK_MODEL=google/gemini-2.5-flash
```

### OpenAI 직접 사용

```env
# API 키
OPENAI_API_KEY=sk-your-openai-api-key

# OpenAI 엔드포인트
OPENAI_BASE_URL=https://api.openai.com/v1

# Main LLM
LLM_MAIN_MODEL=gpt-5-mini

# Task LLM
LLM_TASK_MODEL=gpt-5-nano
```

!!! tip "OpenRouter를 권장하는 이유"
    1. **가성비**: OpenAI 직접 사용 대비 비용 효율적
    2. **속도**: 안건/이슈 추출 과정에서 OpenAI 모델 대비 시간 단축 (LangSmith 트레이스 기반 검증)

!!! info "Dual LLM 전략"
    Doorae는 두 개의 LLM을 분리하여 사용합니다.

    - **Main LLM** (`LLM_MAIN_MODEL`): 에이전트의 대화 응답 생성 -- 고품질 모델 권장
    - **Task LLM** (`LLM_TASK_MODEL`): 멘션 추출, 안건 완료 감지 등 경량 분석 작업 -- 빠르고 저렴한 모델 권장

    이 전략으로 비용을 약 70% 절감할 수 있습니다.

### 기타 설정 옵션

`.env` 파일에서 추가로 설정할 수 있는 주요 항목은 다음과 같습니다.

```env
# LLM 온도 설정
LLM_MAIN_TEMPERATURE=0.7       # Main LLM 온도 (기본값: 0.7)
LLM_TASK_TEMPERATURE=0.0       # Task LLM 온도 (기본값: 0.0)
LLM_TASK_MAX_TOKENS=256        # Task LLM 최대 토큰 (기본값: 256)

# 연결 설정
LLM_TIMEOUT=60.0               # LLM 요청 타임아웃 (초)
LLM_MAX_RETRIES=3              # 재시도 횟수

# 회의 설정
MAX_TURNS=1000                 # 최대 회의 턴 수

# 대화 요약 설정
MAX_MESSAGES_BEFORE_SUMMARY=8  # 이 개수 초과 시 요약 생성
KEEP_RECENT_MESSAGES=3         # 요약 후 유지할 최근 메시지 수
SUMMARY_MAX_TOKENS=3000        # 요약 최대 토큰 수

# MCP 도구 (GitHub 연동 시)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# LangSmith 트레이싱 (선택)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your-langsmith-api-key
# LANGCHAIN_PROJECT=doorae
```

## 4단계: 회의 실행

설정이 완료되면 회의를 시작합니다.

```bash
uv run doorae run --project demo
```

터미널이 TUI (터미널 UI)를 지원하면 자동으로 리치 인터페이스가 표시됩니다.

**예상 출력 (TUI 모드):**

```
┌──────────────── 📋 안건 진행 상태 ────────────────┐
│  🔄 1. 프로젝트 로드맵 논의 (Host) [0:05] ← 현재   │
│  ⏳ 2. 프로젝트 달성 계획 (Host)                    │
│  ⏳ 3. 스프린트 리뷰 (PM)                          │
│  ⏳ 4. 스프린트 계획 (PM)                          │
└───────────────────────────────────────────────────┘

[Host]
안녕하세요, 여러분. 오늘 회의를 시작하겠습니다.
첫 번째 안건은 프로젝트 로드맵 논의입니다...
```

!!! success "축하합니다!"
    첫 AI 팀 회의가 시작되었습니다. 에이전트들이 안건을 따라 자율적으로 대화하며, 모든 안건이 완료되면 회의가 자동으로 종료됩니다.

### 유용한 실행 옵션

```bash
# 커스텀 메시지로 회의 시작
uv run doorae run --project demo --message "긴급 버그 대응 회의"

# TUI 대신 클래식 CLI 모드로 실행
uv run doorae run --project demo --classic

# 상세 로그 출력
uv run doorae run --project demo --verbose

# LangSmith 트레이싱 활성화
uv run doorae run --project demo --trace
```

## 다음 단계

회의를 실행했다면 [첫 번째 회의](first-meeting.md)로 이동하여 회의 진행 과정과 화면 구성 요소를 자세히 알아보세요.
