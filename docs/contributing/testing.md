# 테스트 가이드

Doorae 프로젝트의 테스트 실행 및 작성 방법을 설명합니다.

## 테스트 프레임워크

| 도구 | 용도 |
|------|------|
| [pytest](https://docs.pytest.org/) | 테스트 러너 |
| [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) | 비동기 테스트 지원 |
| [pytest-mock](https://pytest-mock.readthedocs.io/) | Mock 객체 |

!!! info "asyncio 모드"
    `pyproject.toml`에 `asyncio_mode = "auto"`가 설정되어 있어,
    `async def test_*` 함수는 자동으로 비동기 테스트로 인식됩니다.

## 테스트 실행

### 전체 테스트

```bash
uv run pytest
```

### 특정 범위 실행

```bash
# 특정 디렉토리
uv run pytest tests/core/
uv run pytest tests/graph/

# 특정 파일
uv run pytest tests/core/test_profile.py

# 특정 테스트 함수
uv run pytest tests/core/test_profile.py::test_load_agent_profiles

# 키워드 매칭
uv run pytest -k "profile"
```

### 마커 기반 실행

```bash
# Integration 테스트만 실행
uv run pytest -m integration

# Integration 테스트 제외
uv run pytest -m "not integration"
```

### 유용한 옵션

```bash
# 상세 출력
uv run pytest -v

# 첫 번째 실패에서 중단
uv run pytest -x

# 마지막 실패한 테스트만 재실행
uv run pytest --lf

# 출력 캡처 비활성화 (print/logging 확인)
uv run pytest -s
```

## 테스트 구조

테스트 디렉토리는 `doorae/` 패키지 구조를 미러링합니다:

```
tests/
├── conftest.py              # 공통 fixture
├── test_project_setup.py    # 프로젝트 설정 테스트
├── test_tracing.py          # 트레이싱 테스트
├── agents/
│   └── test_base_agent.py   # Agent 기본 클래스 테스트
├── cli/
│   └── test_main.py         # CLI 명령어 테스트
├── config/
│   ├── test_llm_factory.py  # LLM 팩토리 테스트
│   └── test_settings.py     # 설정 테스트
├── core/
│   ├── test_agenda.py       # 안건 처리 테스트
│   ├── test_date_context.py # 날짜 컨텍스트 테스트
│   ├── test_profile.py      # 에이전트 프로필 테스트
│   ├── test_server_address.py
│   └── test_text_utils.py   # 텍스트 유틸리티 테스트
├── graph/
│   ├── nodes/               # 그래프 노드 테스트
│   ├── test_workflow.py     # 워크플로우 테스트
│   ├── test_mediation.py    # 중재 로직 테스트
│   ├── test_state.py        # 상태 관리 테스트
│   └── ...
├── interfaces/
│   ├── test_cli_commands.py # CLI 명령어 테스트
│   ├── test_engine.py       # 엔진 테스트
│   ├── test_tui.py          # TUI 테스트
│   └── ...
├── mcp/
│   └── test_cache.py        # MCP 캐시 테스트
└── server/
    ├── test_room.py         # 회의방 테스트
    ├── test_routes.py       # API 라우트 테스트
    ├── test_connection_manager.py
    ├── test_integration.py  # 통합 테스트
    └── ...
```

!!! tip "파일 이름 규칙"
    - 테스트 파일: `test_<module>.py`
    - 테스트 함수: `test_<설명>()`
    - 테스트 클래스: `Test<클래스명>`

## 테스트 작성

### 기본 패턴

```python
"""doorae.core.profile 테스트."""


def test_load_agent_profiles_returns_list():
    """에이전트 프로필 로드 시 리스트를 반환하는지 확인."""
    profiles = load_agent_profiles(config_path)
    assert isinstance(profiles, list)
    assert len(profiles) > 0
```

### 비동기 테스트

`asyncio_mode = "auto"` 설정 덕분에 별도의 데코레이터가 필요하지 않습니다:

```python
async def test_websocket_connection():
    """WebSocket 연결이 정상적으로 수립되는지 확인."""
    async with connect(server_url) as ws:
        assert ws.open
```

### Fixture 활용

`tests/conftest.py`에 공통 fixture가 정의되어 있습니다:

```python
import pytest


@pytest.fixture
def sample_settings(tmp_path):
    """테스트용 설정 객체를 생성합니다."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test-key\n")
    return Settings(_env_file=env_file)
```

### Mock 활용

외부 API 호출이나 LLM 호출은 반드시 mock 처리합니다:

```python
def test_create_main_llm(mocker):
    """LLM 팩토리가 올바른 모델을 생성하는지 확인."""
    mock_chat = mocker.patch("doorae.config.llm_factory.ChatOpenAI")
    create_main_llm()
    mock_chat.assert_called_once()
```

## 테스트 마커

`pyproject.toml`에 정의된 커스텀 마커:

```python
@pytest.mark.integration
def test_full_meeting_flow():
    """전체 회의 흐름 통합 테스트."""
    ...
```

| 마커 | 용도 | 실행 방법 |
|------|------|----------|
| `integration` | 외부 서비스 연동 테스트 | `pytest -m integration` |

!!! warning "Integration 테스트"
    `integration` 마커가 붙은 테스트는 실제 API 키나 외부 서비스가 필요할 수 있습니다.
    CI 환경에서는 `-m "not integration"`으로 제외하는 것을 권장합니다.

## 테스트 커버리지

커버리지 측정을 위해 `pytest-cov`를 사용할 수 있습니다:

```bash
# 커버리지 측정 (설치 필요)
uv add --dev pytest-cov
uv run pytest --cov=doorae --cov-report=term-missing

# HTML 리포트 생성
uv run pytest --cov=doorae --cov-report=html
# htmlcov/index.html에서 결과 확인
```

## 테스트 작성 가이드라인

!!! success "좋은 테스트의 특징"
    1. **독립적**: 다른 테스트에 의존하지 않습니다
    2. **명확한 이름**: 테스트가 무엇을 검증하는지 이름에서 알 수 있습니다
    3. **하나의 관심사**: 각 테스트는 하나의 동작만 검증합니다
    4. **빠른 실행**: 외부 호출은 mock 처리합니다
    5. **재현 가능**: 실행 환경에 관계없이 동일한 결과를 냅니다

### 새 모듈 테스트 추가 시

1. `tests/` 아래에 대응하는 디렉토리/파일을 생성합니다
2. `__init__.py`를 추가합니다
3. `conftest.py`에 필요한 fixture를 정의합니다
4. 해피 패스, 에러 케이스, 엣지 케이스를 모두 커버합니다

```bash
# 예: doorae/core/new_module.py 테스트 추가
touch tests/core/test_new_module.py
```
