# 설치

이 튜토리얼에서는 Doorae를 로컬 환경에 설치하고, 정상적으로 동작하는지 확인하는 과정을 안내합니다.

## 사전 요구사항

- **Python 3.10 이상**
- **[uv](https://docs.astral.sh/uv/)** (Python 패키지 및 프로젝트 관리 도구)
- **Git**

!!! note "uv 설치"
    uv가 설치되어 있지 않다면 아래 명령어로 먼저 설치하세요.

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

    Windows의 경우:

    ```bash
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

## 1단계: 저장소 클론

```bash
git clone https://github.com/doorae-lab/doorae.git
cd doorae
```

## 2단계: 의존성 설치

```bash
uv sync
```

`uv sync`는 프로젝트의 모든 의존성을 설치하고 가상 환경을 자동으로 구성합니다.

!!! info "서버 모드 의존성"
    WebSocket 서버 모드를 사용하려면 추가 의존성이 필요합니다.

    ```bash
    uv sync --extra server
    ```

## 3단계: 설치 확인

```bash
uv run doorae --version
```

아래와 같은 출력이 나타나면 설치가 정상적으로 완료된 것입니다.

```
Doorae version: 0.1.0
```

## (선택) 글로벌 설치

`uv run` 접두사 없이 `doorae` 명령어를 직접 사용하고 싶다면 글로벌로 설치할 수 있습니다.

```bash
uv tool install .
```

설치 후에는 어디서든 바로 실행할 수 있습니다.

```bash
doorae --version
```

!!! warning "PowerShell 사용자"
    Windows PowerShell에서 `uv tool install .` 후 `doorae` 명령어가 인식되지 않는다면, 아래 명령어를 실행하고 터미널을 재시작하세요.

    ```bash
    uv tool update-shell
    ```

## 디렉터리 구조

설치가 완료된 후의 프로젝트 디렉터리 구조는 다음과 같습니다.

```
doorae/
├── doorae/              # 소스 코드
│   ├── interfaces/      # CLI, TUI 인터페이스
│   ├── graph/           # LangGraph 워크플로우
│   ├── core/            # 프로필, 설정 등 핵심 모듈
│   ├── project/         # 워크스페이스/프로젝트 관리
│   ├── server/          # WebSocket 서버
│   └── templates/       # 프로젝트 스캐폴딩 템플릿
├── config/              # 기본 설정 파일
├── tests/               # 테스트
├── pyproject.toml       # 프로젝트 메타데이터
└── .env.example         # 환경 변수 템플릿
```

## 다음 단계

설치가 완료되었다면 [빠른 시작](quickstart.md)으로 이동하여 첫 프로젝트를 만들고 회의를 실행해 보세요.
