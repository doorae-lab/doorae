# MCP Tool 연동

이 튜토리얼에서는 GitHub MCP server를 설정하고, 에이전트가 GitHub의 실제 이슈와 Pull Request 데이터를 회의에서 활용하도록 구성합니다.

## 사전 준비

- [프로젝트 워크스페이스](project-workspace.md) 튜토리얼을 완료한 상태
- [Go](https://go.dev/dl/) 설치 완료 (GitHub MCP server 실행에 필요)
- GitHub Personal Access Token 발급 완료

## 1단계: GitHub Personal Access Token 발급하기

1. [GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta)에 접속합니다.
2. "Generate new token"을 클릭합니다.
3. 다음 권한을 부여합니다:
   - **Repository access**: 대상 repository 선택
   - **Permissions**: Issues (Read), Pull requests (Read), Contents (Read)
4. 생성된 token을 복사합니다.

## 2단계: .env에 token 설정하기

프로젝트 루트의 `.env` 파일을 열고 token을 설정합니다:

```env
# MCP Tools 설정
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 3단계: mcp_servers.json 확인하기

프로젝트의 `config/mcp_servers.json` 파일을 확인합니다. 기본 scaffold로 생성했다면 이미 GitHub MCP server가 설정되어 있습니다:

```json
{
  "mcpServers": {
    "github": {
      "command": "go",
      "args": [
        "run",
        "github.com/github/github-mcp-server/cmd/github-mcp-server@latest",
        "stdio"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

`${GITHUB_PERSONAL_ACCESS_TOKEN}`은 `.env`에 설정한 값으로 자동 치환됩니다.

## 4단계: 에이전트에 GitHub tool 할당하기

`config/agent_profiles.yaml`에서 GitHub 데이터를 활용할 에이전트에 `mcp_tools` 필드를 추가합니다:

```yaml
agents:
  - name: Host
    role: host
    responsibilities:
      - 회의 시작 인사 및 안건 소개
      - 안건 진행 상황 관리
      - 회의 요약 및 마무리
    expertise:
      - 회의 퍼실리테이션
    phase_triggers: {}

  - name: PM
    role: project_manager
    responsibilities:
      - 프로젝트 일정 관리
      - 이슈 상태 관리
      - 진행 상황 보고
    expertise:
      - 일정 계획
      - 자원 관리
    mcp_tools:
      - github
    metadata:
      target_repository: "doorae-lab/doorae"
      additional_instructions: |
        (IMPORTANT) 도구를 적극적으로 사용하세요.

  - name: TechLead
    role: tech_lead
    responsibilities:
      - 기술 의사결정
      - 아키텍처 설계
    expertise:
      - 시스템 설계
      - 성능 최적화
    mcp_tools:
      - github
    metadata:
      target_repository: "doorae-lab/doorae"
      additional_instructions: |
        (IMPORTANT) 도구를 적극적으로 사용하세요.
```

**핵심 설정:**

- `mcp_tools: ["github"]` -- 이 에이전트가 GitHub MCP server의 도구들을 사용할 수 있게 합니다.
- `metadata.target_repository` -- 에이전트의 system prompt에 포함되어, 어떤 repository를 대상으로 작업할지 알려줍니다.
- `metadata.additional_instructions` -- 도구 사용을 독려하는 추가 지시를 넣을 수 있습니다.

## 5단계: 회의 실행 및 MCP tool 사용 확인하기

```bash
uv run doorae run --project <프로젝트명>
```

MCP tool이 정상적으로 로드되면 다음 메시지가 표시됩니다:

```
✅ MCP 도구 로드 완료: 15개 도구 (1개 서버)
```

회의가 진행되면 PM이나 TechLead가 GitHub 이슈를 조회하며 실제 데이터를 기반으로 발언합니다:

```
[PM]
현재 GitHub 이슈 현황을 확인하겠습니다.

[도구 호출: list_issues]

현재 open 상태인 이슈가 12개 있습니다. 주요 이슈를 보면...
- #45 API 응답 속도 개선 (priority: high)
- #42 문서 업데이트 (priority: medium)
...
```

## MCP 초기화 실패 시 확인사항

MCP tool 로드에 실패하면 다음 메시지가 출력됩니다:

```
⚠️  MCP 도구를 사용할 수 없습니다
   확인 사항:
   1. config/mcp_servers.json 파일 존재 여부
   2. .env 파일의 GITHUB_PERSONAL_ACCESS_TOKEN 설정 여부
```

체크리스트:

1. `go version`으로 Go가 설치되어 있는지 확인합니다.
2. `.env`의 `GITHUB_PERSONAL_ACCESS_TOKEN`이 유효한 token인지 확인합니다.
3. `config/mcp_servers.json` 파일이 올바른 JSON 형식인지 확인합니다.
4. 네트워크 연결을 확인합니다 (GitHub MCP server는 처음 실행 시 패키지를 다운로드합니다).

## 다음 단계

- [커스텀 에이전트 프로필](custom-agent-profiles.md) - 에이전트별 역할과 전문성 커스터마이징
- [Server 모드와 멀티플레이어](server-mode-multiplayer.md) - 여러 사람이 함께 참여하는 회의
