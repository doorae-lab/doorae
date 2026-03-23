# Doorae

**에이전트 간 자율 협업이 가능한 오픈소스 AI 팀 워크스페이스**

---

Doorae는 AI 에이전트들이 역할별로 모여 구조화된 회의를 진행하고, 안건을 논의하며, 실행 가능한 결과물을 만들어내는 시스템입니다. [LangGraph](https://github.com/langchain-ai/langgraph) 기반의 워크플로우 위에서 에이전트 간 자율 대화, 계층적 위임, 멀티 런타임을 지원합니다.

```bash
$ doorae run --project demo
```

```
┌──────────────── 📋 Agenda Status ────────────────┐
│  🔄 1. Project Roadmap Discussion (Host) [2:15] ← │
│  ⏳ 2. Sprint Review (PM)                         │
│  ⏳ 3. Sprint Planning (TechLead)                  │
└───────────────────────────────────────────────────┘

[Host]
Hello everyone, let's begin today's sprint meeting...
```

## 주요 특징

- **에이전트 자율 협업** — 에이전트끼리 직접 대화하고 작업을 위임합니다
- **계층적 위임** — Supervisor가 Sub-agent에게 작업을 분배합니다 (예: TechLead → Backend, Frontend)
- **안건 기반 워크플로우** — 안건별 필수 발언자, 자동 진행, 완료 감지
- **멀티 런타임** — OpenHands, Claude Agent SDK 등 다양한 에이전트 런타임 지원 (계획 중)
- **Dual LLM 전략** — Main LLM(대화) + Task LLM(분석)으로 70% 비용 절감
- **MCP 도구 통합** — GitHub 등 외부 도구를 에이전트에 바인딩
- **다중 인터페이스** — TUI (터미널 UI), CLI, WebSocket 서버 모드
- **오픈소스** — 완전한 코드 접근, 자체 호스팅 가능

!!! warning "Pre-alpha"
    Doorae는 초기 개발 단계입니다. API, 설정, 워크플로우가 예고 없이 변경될 수 있습니다.

## 빠른 시작

```bash
git clone https://github.com/doorae-lab/doorae.git
cd doorae
uv sync
uv run doorae init
uv run doorae project create demo
# .env 파일에 API 키 설정 후
uv run doorae run --project demo
```

자세한 내용은 [시작하기](getting-started/index.md)를 참고하세요.

## 문서 구조

| 섹션 | 목적 | 대상 |
|------|------|------|
| [시작하기](getting-started/index.md) | 설치부터 첫 회의까지 | 처음 접하는 사용자 |
| [튜토리얼](tutorials/index.md) | 기능별 학습 가이드 | 기능을 배우고 싶은 사용자 |
| [사용 가이드](guides/index.md) | 특정 목표 달성 방법 | 실무에서 사용 중인 사용자 |
| [레퍼런스](reference/index.md) | 설정, API, 스키마 상세 | 정확한 값을 찾는 사용자 |
| [아키텍처](architecture/index.md) | 시스템 설계와 기술 명세 | 기여자, 내부 구조를 이해하고 싶은 사용자 |
| [로드맵](roadmap/index.md) | 향후 계획과 비전 | 프로젝트 방향이 궁금한 사용자 |
| [기여하기](contributing/index.md) | 개발 참여 방법 | 기여자 |

## 기술 스택

[LangGraph](https://github.com/langchain-ai/langgraph) |
[LangChain](https://github.com/langchain-ai/langchain) |
[Textual](https://github.com/Textualize/textual) |
[Typer](https://github.com/tiangolo/typer) |
[Pydantic](https://github.com/pydantic/pydantic) |
[FastAPI](https://github.com/tiangolo/fastapi)
