# TheTable

AI 에이전트 기반 팀 회의 시스템

## 프로젝트 소개

TheTable은 AI 에이전트 기반 팀 회의 시스템입니다. 여러 AI 에이전트가 참여하여 회의를 진행하고, 안건(이슈)을 추출하며, 회의록을 자동으로 생성합니다.

### 주요 기능
- 🤖 다중 AI 에이전트 기반 회의 진행
- 📝 실시간 회의록 자동 생성
- 🎯 안건(이슈) 자동 추출 및 추적
- 💬 멘션 기반 에이전트 호출
- 🔄 회의 상태 자동 관리 및 종료 감지

## 설치 방법

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용합니다.

### 1. uv 설치
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 프로젝트 클론 및 의존성 설치
```bash
git clone https://github.com/yaklevel/thetable.git
cd thetable
uv sync
```

### 3. 환경 설정
`.env.example` 파일을 `.env`로 복사하고 필요한 값을 설정합니다:

```bash
cp .env.example .env
```

## 환경 설정 가이드

### 추천 모델 설정

| Provider | MAIN MODEL | TASK MODEL |
|----------|------------|------------|
| **OpenRouter** (권장) | `deepseek/deepseek-v3.2` | `google/gemini-2.5-flash` |
| OpenAI | `gpt-5-mini` | `gpt-5-nano` |

### OpenRouter 사용 (권장)

**권장 이유:**
1. **가성비**: OpenAI 직접 사용 대비 비용 효율적
2. **속도**: 아젠다/이슈 추출 과정에서 더 빠른 처리 (LangSmith trace 기반)

**설정 방법:**

1. [OpenRouter](https://openrouter.ai/)에서 API 키 발급
2. `.env` 파일 설정:

```bash
# API 키 설정
OPENAI_API_KEY=your-openrouter-api-key-here

# Base URL 설정 (OpenRouter)
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# 모델 설정
LLM_MAIN_MODEL=deepseek/deepseek-v3.2
LLM_TASK_MODEL=google/gemini-2.5-flash
```

### OpenAI 직접 사용

1. [OpenAI](https://platform.openai.com/)에서 API 키 발급
2. `.env` 파일 설정:

```bash
# API 키 설정
OPENAI_API_KEY=your-openai-api-key-here

# Base URL 설정 (OpenAI 기본값 사용 시 주석 처리 또는 삭제)
# OPENAI_BASE_URL=https://api.openai.com/v1

# 모델 설정
LLM_MAIN_MODEL=gpt-5-mini
LLM_TASK_MODEL=gpt-5-nano
```

### 기타 설정 옵션

#### GitHub MCP Tools (선택사항)
GitHub 이슈 연동 기능을 사용하려면 GitHub Personal Access Token이 필요합니다:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_actual_token_here
```

#### LangSmith Tracing (선택사항)
LLM 호출 추적 및 디버깅을 위해 LangSmith를 사용할 수 있습니다:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=thetable-meeting
```

## 실행 방법

### CLI 모드로 실행

```bash
uv run thetable
```

또는

```bash
uv run python -m thetable.interfaces.cli
```

### 개발 모드 실행

```bash
# 테스트 실행
uv run pytest

# 특정 테스트 실행
uv run pytest tests/test_specific.py

# 통합 테스트 제외
uv run pytest -m "not integration"
```

## 패키지 관리

### 의존성 추가
```bash
uv add <package_name>
```

### 개발 의존성 추가
```bash
uv add --dev <package_name>
```

## 프로젝트 구조

```
thetable/
├── config/              # 설정 파일 (에이전트 프로필 등)
├── examples/            # 예제 코드
├── scripts/             # 유틸리티 스크립트
├── tests/              # 테스트 코드
├── thetable/           # 메인 패키지
│   ├── agents/         # 에이전트 구현
│   ├── core/           # 핵심 로직
│   ├── interfaces/     # CLI 등 인터페이스
│   └── utils/          # 유틸리티
└── pyproject.toml      # 프로젝트 설정
```

## 라이선스

이 프로젝트는 Apache License 2.0 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여

기여는 언제나 환영합니다! 이슈나 Pull Request를 자유롭게 제출해 주세요.

## 문의

문제가 발생하거나 질문이 있으시면 [GitHub Issues](https://github.com/yaklevel/thetable/issues)를 통해 문의해 주세요.
