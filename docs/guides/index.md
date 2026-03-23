# How-to Guides

Doorae 사용 시 자주 마주치는 실전 과제를 해결하기 위한 가이드 모음입니다.

---

## 시작하기

| 가이드 | 설명 |
|--------|------|
| [CLI 명령어 가이드](cli-commands.md) | `run`, `init`, `serve`, `create`, `join`, `rooms` 등 모든 CLI 명령어의 실전 사용법 |
| [TUI 인터페이스 가이드](tui-interface.md) | 회의 중 화면 구성, 키보드 단축키, 안건 패널 읽는 법 |

## 에이전트 설정

| 가이드 | 설명 |
|--------|------|
| [에이전트별 LLM 설정](per-agent-llm.md) | 에이전트마다 다른 모델 지정, 환경변수 치환, fallback chain |
| [계층적 위임 구조](hierarchical-delegation.md) | supervisor/sub-agent 계층 구성, `ask_{agent}` tool 동작 원리 |

## 서버 운영

| 가이드 | 설명 |
|--------|------|
| [서버 운영 가이드](server-operation.md) | FastAPI 서버 배포, 환경변수 설정, Room lifecycle, WebSocket 클라이언트 연동 |

## 모니터링 & 최적화

| 가이드 | 설명 |
|--------|------|
| [LangSmith 추적 설정](langsmith-tracing.md) | `--trace` 플래그, 환경변수 설정, 프로젝트별 추적 |
| [비용 최적화](cost-optimization.md) | Dual LLM 전략, 모델 조합 추천, MCP 캐싱, 요약 설정 튜닝 |

## 문제 해결

| 가이드 | 설명 |
|--------|------|
| [트러블슈팅](troubleshooting.md) | API key 오류, MCP 초기화 실패, 무한루프, WebSocket 연결 등 자주 발생하는 문제와 해결법 |
