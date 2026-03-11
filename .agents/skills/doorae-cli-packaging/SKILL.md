---
name: doorae-cli-packaging
description: Use when changing packaging, installation UX, or CLI entrypoints for this repository. Covers the `doorae` distribution name, legacy `thetable` compatibility, `uv tool install` behavior on Windows PowerShell, and the validation steps needed before closing packaging-related issues.
---

# Doorae CLI Packaging

Use this skill when work changes how the repository is installed or how users invoke the CLI.

## Goals

- Keep the install target named `doorae`.
- Keep internal Python package imports on `thetable` until a dedicated rename effort happens.
- Preserve legacy entrypoints while `doorae` becomes the primary user-facing command.
- Make `--help` and `--version` paths side-effect free.

## Files to check

- `pyproject.toml`
- `doorae/__init__.py`
- `doorae/__main__.py`
- `thetable/__main__.py`
- `thetable/interfaces/cli.py`
- `tests/cli/test_main.py`
- `tests/test_project_setup.py`
- `README.md`

## Packaging rules

- Set `[project].name` to `doorae` when validating the user-facing install path.
- Keep console scripts for both commands during the transition:
  - `doorae = "thetable.interfaces.cli:doorae_main"`
  - `thetable = "thetable.interfaces.cli:thetable_main"`
- Keep `python -m doorae` working by shipping a small wrapper package under `doorae/`.
- Keep `python -m thetable` working by pointing `thetable/__main__.py` at `thetable_main()`.
- If the wheel needs to ship both packages, declare them explicitly in Hatch build config.

## CLI guardrails

- Do not import workflow-heavy modules at CLI import time if the command only needs help or version output.
- `doorae --help`, `thetable --help`, `python -m doorae --help`, and `python -m thetable --help` should not emit debug logs.
- Keep placeholder commands explicit. If `init` or `project create` are not implemented yet, fail with a clear message and exit code 1.

## Validation path

Preferred local validation:

1. Create or reuse `.venv`.
2. Install editable with dev dependencies.
3. Run focused CLI tests.
4. Run command-level smoke tests.

Commands:

```powershell
I:\dule\.venv\Scripts\python.exe -m pip install -e "I:\dule[dev]"
I:\dule\.venv\Scripts\python.exe -m pytest I:\dule\tests\cli\test_main.py I:\dule\tests\test_project_setup.py -q
I:\dule\.venv\Scripts\doorae.exe --help
I:\dule\.venv\Scripts\python.exe -m doorae --help
I:\dule\.venv\Scripts\thetable.exe --help
I:\dule\.venv\Scripts\python.exe -m thetable --help
I:\dule\.venv\Scripts\python.exe -m pip show doorae
```

## `uv tool install` notes on Windows

- `uv tool install .` is the user-facing install path to document.
- PowerShell users often need `uv tool update-shell` and a new terminal before `doorae` resolves from PATH.
- If immediate verification is needed in the current session, add:

```powershell
$env:PATH = "C:\Users\$env:USERNAME\.local\bin;$env:PATH"
```

- If PATH must be made persistent manually, add `C:\Users\<user>\.local\bin` to the user PATH and reopen the shell.

## Documentation rules

- README install examples should use `doorae`, not `thetable`.
- Keep one compatibility note for `thetable` only if the repository still supports it.
- If `uv tool install .` is documented, also document the shell refresh step.
