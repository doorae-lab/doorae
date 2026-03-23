# 개발 환경 설정

이 가이드는 Doorae 프로젝트를 로컬에서 개발하기 위한 환경 설정 방법을 설명합니다.

## 필수 요구사항

| 도구 | 최소 버전 | 용도 |
|------|----------|------|
| Python | 3.10+ | 런타임 |
| [uv](https://docs.astral.sh/uv/) | 최신 | 패키지 매니저 |
| Git | 2.0+ | 버전 관리 |

!!! tip "uv 설치"
    `uv`는 Rust로 작성된 빠른 Python 패키지 매니저입니다.
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

## Fork & Clone

```bash
# 1. GitHub에서 Doorae 저장소를 Fork합니다

# 2. Fork한 저장소를 Clone합니다
git clone https://github.com/<your-username>/thetable.git
cd thetable

# 3. Upstream remote를 추가합니다
git remote add upstream https://github.com/<org>/thetable.git
```

## 의존성 설치

`uv sync`를 사용하면 모든 의존성이 자동으로 설치됩니다.

```bash
# 기본 의존성 + 개발 의존성 설치
uv sync
```

!!! info "주요 의존성"
    `pyproject.toml`에 정의된 핵심 의존성:

    - **langgraph** / **langchain** - AI 워크플로우 엔진
    - **langchain-openai** - OpenAI LLM 연동
    - **langchain-mcp-adapters** - MCP 서버 연동
    - **pydantic** / **pydantic-settings** - 설정 관리
    - **typer** - CLI 프레임워크
    - **textual** - TUI 프레임워크
    - **websockets** / **httpx** - 네트워크 통신
    - **fastapi** / **uvicorn** - 서버 (선택 의존성)

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다. 템플릿은 `doorae/templates/default/.env.example`에 있습니다.

```bash
# 템플릿 복사
cp doorae/templates/default/.env.example .env
```

`.env` 파일을 열고 필요한 값을 설정합니다:

```bash
# .env (필수)
OPENAI_API_KEY=sk-...           # OpenAI API 키

# .env (선택)
LANGSMITH_API_KEY=lsv2-...      # LangSmith 트레이싱 (선택)
LANGSMITH_TRACING=true
```

!!! warning "보안 주의"
    `.env` 파일은 `.gitignore`에 포함되어 있습니다. **절대로 API 키를 커밋하지 마세요.**

## 로컬 실행

### CLI 모드 (단독 실행)

```bash
# 대화형 회의 시작
uv run doorae run

# 프로젝트 지정 실행
uv run doorae run --project <project-name>
```

### 서버 모드

```bash
# WebSocket 서버 시작
uv run doorae serve

# 특정 주소/포트 지정
uv run doorae serve --server 0.0.0.0:8080
```

### TUI 클라이언트

```bash
# TUI로 서버에 접속
uv run doorae join --server ws://localhost:8000
```

## 테스트 실행

```bash
# 전체 테스트
uv run pytest

# 특정 모듈 테스트
uv run pytest tests/core/

# Integration 테스트 제외
uv run pytest -m "not integration"
```

자세한 내용은 [테스트 가이드](testing.md)를 참고하세요.

## IDE 설정

### VS Code

추천 확장:

- **Python** (ms-python.python) - Python 언어 지원
- **Pylance** (ms-python.vscode-pylance) - 타입 체크
- **Ruff** (charliermarsh.ruff) - Linter/Formatter

`.vscode/settings.json` 예시:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

### PyCharm

1. **Project Interpreter**: `.venv/bin/python`을 선택합니다
2. **Test Runner**: pytest를 기본 테스트 러너로 설정합니다
3. **Mark Directory**: `tests/`를 Test Sources Root로 지정합니다

## 프로젝트 구조 초기화

Doorae는 workspace/project 구조를 사용합니다:

```bash
# 워크스페이스 초기화
uv run doorae init

# 새 프로젝트 생성
uv run doorae new <project-name>
```

이 명령은 `.doorae/` 디렉토리에 워크스페이스 설정을 생성합니다.

## 다음 단계

- [코드 구조](code-structure.md)를 파악하여 프로젝트 이해도를 높이세요
- [테스트 가이드](testing.md)를 읽고 테스트 작성 방법을 익히세요
- GitHub Issues에서 `good first issue` 라벨이 붙은 이슈를 찾아보세요
