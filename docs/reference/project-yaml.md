# Project YAML Reference

소스: `doorae/project/models.py` -- `ProjectConfig`

`project.yaml`은 `.doorae/projects/<slug>/project.yaml`에 위치하며, 하나의 scaffold project 메타데이터를 담는다. `doorae project create` 명령으로 자동 생성된다.

## 파일 위치

```
.doorae/
  projects/
    <slug>/
      project.yaml          # 이 파일
      config/
        agent_profiles.yaml
        agendas.yaml
        mcp_servers.json
```

## 필드

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `name` | `str` | O | | 프로젝트 표시 이름. 비어 있을 수 없다 |
| `slug` | `str` | O | | 파일시스템 안전 식별자. 비어 있을 수 없다 |
| `version` | `int` | | `1` | 설정 스키마 버전 |
| `agent_profiles_path` | `str` | | `"config/agent_profiles.yaml"` | Agent 프로필 파일 상대 경로 (project 디렉터리 기준) |
| `agendas_path` | `str` | | `"config/agendas.yaml"` | 안건 파일 상대 경로 (project 디렉터리 기준) |
| `mcp_servers_path` | `str` | | `"config/mcp_servers.json"` | MCP 서버 설정 파일 상대 경로 (project 디렉터리 기준) |

모든 문자열 필드는 비어 있을 수 없다. 유효성 검사에 실패하면 `ValueError`가 발생한다. `from_dict()`에 dict가 아닌 값을 전달하면 `TypeError`가 발생한다.

## 경로 해석

`agent_profiles_path`와 `agendas_path`는 project 디렉터리를 기준으로 하는 상대 경로다. `doorae run` 실행 시 `resolve_project_run()`이 이 경로를 절대 경로로 변환하고 파일 존재 여부를 검증한다. 파일이 없으면 `ProjectConfigError`가 발생한다.

## 예시

```yaml
version: 1
name: My Team Meeting
slug: my-team-meeting
agent_profiles_path: config/agent_profiles.yaml
agendas_path: config/agendas.yaml
mcp_servers_path: config/mcp_servers.json
```
