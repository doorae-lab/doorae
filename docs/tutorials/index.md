# 튜토리얼

Doorae의 핵심 기능을 단계별로 배워봅니다. 각 튜토리얼은 독립적으로 진행할 수 있지만, 처음이라면 위에서부터 순서대로 따라하는 것을 권장합니다.

## 학습 경로

### 입문 (Beginner)

| 순서 | 튜토리얼 | 설명 | 소요 시간 |
|------|----------|------|-----------|
| 1 | [LLM Provider 설정](llm-provider-setup.md) | OpenAI, OpenRouter, Azure OpenAI, Ollama 등 다양한 LLM provider를 설정합니다 | 10분 |
| 2 | [프로젝트 워크스페이스](project-workspace.md) | `doorae init`과 `doorae project create`로 워크스페이스를 구성합니다 | 10분 |
| 3 | [안건(Agenda) 설정](configure-agendas.md) | `agendas.yaml`을 작성하여 회의 안건 흐름을 제어합니다 | 15분 |

### 중급 (Intermediate)

| 순서 | 튜토리얼 | 설명 | 소요 시간 |
|------|----------|------|-----------|
| 4 | [커스텀 에이전트 프로필](custom-agent-profiles.md) | 새로운 AI 에이전트를 추가하고 역할을 정의합니다 | 15분 |
| 5 | [사람이 회의에 참여하기](human-participation.md) | `is_human: true`로 실제 사용자가 AI 에이전트와 함께 회의합니다 | 15분 |
| 6 | [MCP Tool 연동](mcp-tool-integration.md) | GitHub MCP server를 연결하여 에이전트가 실제 데이터를 활용하게 합니다 | 20분 |

### 고급 (Advanced)

| 순서 | 튜토리얼 | 설명 | 소요 시간 |
|------|----------|------|-----------|
| 7 | [Server 모드와 멀티플레이어](server-mode-multiplayer.md) | WebSocket 서버를 띄우고 여러 사람이 동시에 회의에 참여합니다 | 20분 |

## 사전 준비

모든 튜토리얼을 시작하기 전에 다음이 준비되어 있어야 합니다:

- Python 3.10 이상
- [uv](https://docs.astral.sh/uv/) 설치 완료
- Doorae 클론 및 의존성 설치:

```bash
git clone https://github.com/doorae-lab/doorae.git
cd doorae
uv sync
```

- OpenAI 호환 API key (OpenAI, OpenRouter 등)
