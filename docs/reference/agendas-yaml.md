# Agendas YAML Reference

소스: `doorae/core/agenda.py`, `doorae/graph/state.py`

`agendas.yaml` 파일은 회의 안건 목록을 정의한다. 최상위 키는 `agendas`이며 안건 딕셔너리의 리스트를 포함한다.

## 로딩

`load_agendas(yaml_path)` 함수가 YAML 파일을 읽어 `agendas` 키의 값을 `list[dict]`로 반환한다. 파일이 비어 있거나 `agendas` 키가 없으면 빈 리스트를 반환한다.

## 입력 필드 (YAML에서 정의)

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `title` | `str` | O | | 안건 제목 |
| `description` | `str` | | `""` | 안건 상세 설명 |
| `required_speakers` | `List[str]` | | `[]` | 이 안건에서 발언해야 할 참여자 이름 목록 |

## 런타임 필드 (MeetingState의 Agenda 모델)

소스: `doorae/graph/state.py` -- `Agenda` 클래스

YAML에서 로드된 후 런타임에 다음 필드가 추가된다.

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `status` | `str` | `"pending"` | 안건 상태. `"pending"`, `"in_progress"`, `"completed"`, `"deferred"` |
| `owner` | `Optional[str]` | `None` | 안건 담당자 |
| `decision` | `Optional[str]` | `None` | 결정 사항 |
| `time_limit` | `int` | `300` | 시간 제한 (초 단위, 기본 5분) |
| `start_time` | `Optional[float]` | `None` | 안건 시작 시간 (Unix timestamp) |
| `end_time` | `Optional[float]` | `None` | 안건 종료 시간 (Unix timestamp) |

## 안건 상태

| 상태 | 아이콘 | 텍스트 | 설명 |
|------|--------|--------|------|
| `pending` | ⏳ | 예정 | 아직 시작되지 않은 안건 |
| `in_progress` | 🔄 | 현재 논의 중 | 현재 논의 중인 안건 |
| `completed` | ✅ | 완료 | 논의가 완료된 안건 |
| `deferred` | ⏸️ | 보류 | 보류된 안건 |

## 예시

```yaml
agendas:
  - title: "프로젝트 로드맵 논의"
    description: "프로젝트 로드맵을 논의하고 달성 계획을 수립합니다"
    required_speakers: ["Host", "PM", "TechLead"]

  - title: "스프린트 리뷰"
    description: "스프린트 리뷰를 진행합니다"
    required_speakers: ["PM", "TechLead"]

  - title: "스프린트 계획"
    description: "스프린트 계획을 수립합니다"
    required_speakers: ["PM", "TechLead"]
```
