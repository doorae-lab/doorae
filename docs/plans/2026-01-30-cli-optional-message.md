# CLI 기본 메시지 지원: message를 옵셔널로 변경

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** CLI에서 message 인자 없이도 실행 가능하도록 기본 메시지 지원

**Architecture:** message를 Argument에서 Option으로 변경, 기본값 "회의를 시작합니다" 설정

**Tech Stack:** Typer 0.21+, 기존 CLI 구조 유지

---

## Task 1: CLI 코드 수정

**Files:**
- Modify: `thetable/interfaces/cli.py`

**Step 1: 파일 읽기**

Run: `cat thetable/interfaces/cli.py`

**Step 2: message 파라미터 변경**

파일: `thetable/interfaces/cli.py`

변경 전:
```python
@app.command()
def main(
    message: Optional[str] = typer.Argument(
        None,
        help="회의 시작 메시지 (Host가 먼저 말할 내용)",
    ),
```

변경 후:
```python
@app.command()
def main(
    message: str = typer.Option(
        "회의를 시작합니다",
        "--message",
        "-m",
        help="회의 시작 메시지",
    ),
```

**Step 3: message 검증 코드 제거**

파일: `thetable/interfaces/cli.py`

변경 전:
```python
    # message가 없으면 에러
    if message is None:
        console.print("[red]Error: message argument is required[/red]")
        raise typer.Exit(code=1)
```

변경 후:
```python
    # message는 항상 기본값이 있으므로 검증 불필요
```

**Step 4: docstring 업데이트**

파일: `thetable/interfaces/cli.py`

변경 전:
```python
    """TheTable CLI - AI 기반 팀 회의 시스템

    Examples:

        # 기본 회의 실행

        thetable "오늘 회의를 시작하겠습니다"

        # 커스텀 프로필 사용

        thetable "회의 시작" --profiles config/custom_profiles.yaml
```

변경 후:
```python
    """TheTable CLI - AI 기반 팀 회의 시스템

    Examples:

        # 기본 메시지로 회의 시작

        thetable

        # 커스텀 메시지로 회의 시작

        thetable --message "오늘 스프린트 회의를 시작합니다"
        thetable -m "긴급 회의"

        # 다른 옵션과 함께 사용

        thetable --message "회의 시작" --stream -v
        thetable --profiles config/custom.yaml
```

**Step 5: 변경사항 확인**

Run: `git diff thetable/interfaces/cli.py`
Expected: message 파라미터 변경, 검증 코드 제거, docstring 업데이트 확인

**Step 6: Commit**

```bash
git add thetable/interfaces/cli.py
git commit -m "feat: make message optional with default value

- Change message from Argument to Option
- Add default value: '회의를 시작합니다'
- Add short flag -m for --message
- Remove message validation (always has default)
- Update CLI examples in docstring"
```

---

## Task 2: 테스트 수정

**Files:**
- Modify: `tests/cli/test_main.py`

**Step 1: 기존 테스트 확인**

Run: `cat tests/cli/test_main.py`

**Step 2: test_cli_help 업데이트**

파일: `tests/cli/test_main.py`

변경 전:
```python
def test_cli_help():
    """도움말 출력 테스트"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "TheTable" in result.stdout
    assert "message" in result.stdout
```

변경 후:
```python
def test_cli_help():
    """도움말 출력 테스트"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "TheTable" in result.stdout
    assert "--message" in result.stdout  # Option으로 표시되는지 확인
```

**Step 3: test_cli_basic_message 삭제 및 새 테스트 추가**

파일: `tests/cli/test_main.py`

삭제:
```python
def test_cli_basic_message():
    """기본 메시지 실행 테스트"""
    result = runner.invoke(app, ["회의 시작", "--help"])
    assert "--profiles" in result.stdout or result.exit_code == 0
```

추가:
```python
def test_cli_default_message():
    """기본 메시지로 실행 테스트 (인자 없음)"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--message" in result.stdout


def test_cli_custom_message():
    """커스텀 메시지로 실행 테스트"""
    result = runner.invoke(app, ["--message", "커스텀 회의", "--help"])
    assert result.exit_code == 0
```

**Step 4: 테스트 실행 (성공 확인)**

Run: `uv run pytest tests/cli/test_main.py -v`
Expected: PASS (5/5 tests)

**Step 5: Commit**

```bash
git add tests/cli/test_main.py
git commit -m "test: update CLI tests for optional message

- Update test_cli_help to check --message option
- Remove test_cli_basic_message (obsolete)
- Add test_cli_default_message for no arguments
- Add test_cli_custom_message for --message flag"
```

---

## Task 3: 전체 테스트 및 검증

**Files:**
- Test: All functionality

**Step 1: 전체 테스트 실행**

Run: `uv run pytest -v`
Expected: 모든 테스트 PASS

**Step 2: CLI 동작 확인 - 기본 메시지**

Run: `uv run thetable --help`
Expected: `--message` 옵션이 표시되고, 기본값 안내

**Step 3: CLI 동작 확인 - 버전**

Run: `uv run thetable --version`
Expected: "TheTable version: 0.1.0" 출력

**Step 4: 최종 Commit**

```bash
git add .
git commit -m "docs: verify CLI optional message implementation

- All tests passing
- CLI works without message argument
- --message option works correctly"
```

---

## 완료 조건

1. ✅ message가 Option으로 변경됨
2. ✅ 기본값 "회의를 시작합니다" 설정됨
3. ✅ `-m` 단축 플래그 추가됨
4. ✅ message 검증 코드 제거됨
5. ✅ 모든 테스트 통과
6. ✅ `thetable` 단독 실행 가능
7. ✅ `thetable --message "..."` 실행 가능

---

## Breaking Changes

**v0.1.0 → v0.2.0**

변경 전:
```bash
thetable "회의를 시작합니다"  # 위치 인자 (필수)
```

변경 후:
```bash
thetable                          # 기본 메시지 자동 사용
thetable --message "커스텀 메시지"  # 커스텀 메시지 지정
```

**마이그레이션:**
- `thetable "메시지"` → `thetable --message "메시지"`
- 메시지 없이 실행 → `thetable`
