# Workspace YAML Reference

소스: `doorae/project/models.py` -- `WorkspaceConfig`

`workspace.yaml`은 `.doorae/workspace.yaml`에 위치하며, Doorae 워크스페이스의 전역 메타데이터를 담는다. `doorae init` 명령으로 생성된다.

## 파일 위치

```
.doorae/
  workspace.yaml    # 이 파일
  projects/
    <slug>/
      project.yaml
      config/
        ...
```

## 필드

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `version` | `int` | | `1` | 설정 스키마 버전 |
| `current_project` | `str \| None` | | `None` | 현재 활성 프로젝트 slug. `doorae run`에서 `--project` 미지정 시 이 값을 사용 |
| `projects_dir` | `str` | | `".doorae/projects"` | 프로젝트 디렉터리 경로 (워크스페이스 루트 기준 상대 경로) |

## 파싱

`WorkspaceConfig.from_dict(raw)` 메서드가 YAML에서 읽은 딕셔너리를 파싱한다.

- `raw`가 dict가 아니면 기본값으로 `WorkspaceConfig()`를 반환한다
- `current_project`가 `None`이 아니고 문자열이 아니면 `str()`로 변환한다
- `version`은 `int()`로 변환한다

## 예시

```yaml
version: 1
current_project: my-team-meeting
projects_dir: .doorae/projects
```

### 초기 생성 시 기본값

`doorae init` 실행 직후의 내용:

```yaml
version: 1
current_project: null
projects_dir: .doorae/projects
```
