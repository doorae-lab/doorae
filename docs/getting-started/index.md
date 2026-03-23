# 시작하기

Doorae를 설치하고, 프로젝트를 만들고, 첫 AI 팀 회의를 실행하기까지의 과정을 안내합니다.

## 사전 요구사항

시작하기 전에 아래 도구들이 설치되어 있는지 확인하세요.

| 도구 | 최소 버전 | 확인 명령어 |
|------|-----------|------------|
| Python | 3.10+ | `python3 --version` |
| [uv](https://docs.astral.sh/uv/) | 최신 권장 | `uv --version` |
| Git | - | `git --version` |

!!! tip "uv가 없다면"
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

또한 OpenAI-호환 API 키가 필요합니다. OpenAI, [OpenRouter](https://openrouter.ai/), Azure OpenAI 등을 사용할 수 있습니다.

## 학습 경로

아래 순서대로 진행하면 처음부터 끝까지 원활하게 따라 할 수 있습니다.

### 1. [설치](installation.md)

저장소 클론, 의존성 설치, `doorae` 명령어 확인까지의 과정입니다.

### 2. [빠른 시작](quickstart.md)

워크스페이스 초기화, 프로젝트 생성, `.env` 설정, 회의 실행까지의 핵심 흐름을 다룹니다.

### 3. [첫 번째 회의](first-meeting.md)

회의가 진행되는 동안 화면에 표시되는 요소들을 이해하고, TUI와 CLI 모드의 차이를 배웁니다.

## 다음 단계

시작하기를 완료한 후에는 다음 문서를 참고하세요.

- [에이전트 프로필 커스터마이징](../tutorials/custom-agent-profiles.md) -- 회의 참여자를 원하는 대로 구성
- [안건 설정하기](../tutorials/configure-agendas.md) -- 회의 안건을 프로젝트에 맞게 변경
- [MCP 도구 연동하기](../tutorials/mcp-tool-integration.md) -- GitHub 등 외부 도구를 에이전트에 연결
- [LLM 제공자 설정](../tutorials/llm-provider-setup.md) -- OpenRouter, OpenAI, Azure, Ollama 등 다양한 제공자 설정
