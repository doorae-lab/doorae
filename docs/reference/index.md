# Reference

Doorae reference 문서 모음. 각 페이지는 소스 코드의 실제 구현에 기반한다.

## CLI

| 페이지 | 설명 |
|--------|------|
| [CLI](cli.md) | `doorae` 명령어, 서브커맨드, 옵션 전체 목록 |

## 설정

| 페이지 | 설명 |
|--------|------|
| [환경 변수](environment-variables.md) | `.env` 파일의 모든 환경 변수, 타입, 기본값, fallback 체인 |
| [Agent Profiles YAML](agent-profiles-yaml.md) | `agent_profiles.yaml`의 `AgentProfile` 모델 필드 정의 |
| [Agendas YAML](agendas-yaml.md) | `agendas.yaml`의 안건 구조 |
| [MCP Servers JSON](mcp-servers-json.md) | `mcp_servers.json`의 MCP 서버 설정 구조 |
| [Project YAML](project-yaml.md) | `.doorae/projects/<slug>/project.yaml` 구조 |
| [Workspace YAML](workspace-yaml.md) | `.doorae/workspace.yaml` 구조 |

## Server

| 페이지 | 설명 |
|--------|------|
| [Server API](server-api.md) | REST endpoint, WebSocket endpoint, 요청/응답 모델 |

## 내부 구조

| 페이지 | 설명 |
|--------|------|
| [Meeting State](meeting-state.md) | `MeetingState` TypedDict 필드 전체 |
| [Event Protocol](event-protocol.md) | `MeetingEngineCallback` protocol 메서드 및 WebSocket 이벤트 형식 |
