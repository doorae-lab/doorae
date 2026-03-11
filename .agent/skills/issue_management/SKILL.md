---
name: issue-management
description: Use when checking, creating, updating, syncing, or triaging GitHub issues in this repository via scripts/issue_manager.py and direct GitHub API reads.
---

# Issue Management

Use this skill for GitHub issue operations in this repository.

## Primary tools

- `scripts/issue_manager.py`
- direct GitHub REST calls with the token in `.env` when the script does not expose the read path you need

If network access is blocked, request escalation instead of guessing from stale local state.

## Commands

- check: `python scripts/issue_manager.py check --title "<title>"`
- create: `python scripts/issue_manager.py create --title "<title>" --body "<body>"`
- update: `python scripts/issue_manager.py update --number <n> --body "<body>"`
- sync: `python scripts/issue_manager.py sync`
- push local spec: `python scripts/issue_manager.py push <path>`
- push all specs: `python scripts/issue_manager.py push-all`
- create PR: `python scripts/issue_manager.py create-pr --title "<title>" --body "<body>" --head <branch> --base <branch>`

## Required workflow

1. Check for duplicates before creating a new issue.
2. Choose a UTF-8-safe write path before creating or updating any issue with non-ASCII text.
3. Keep one issue to one concrete outcome.
4. If an issue is larger than 1-2 work sessions, split it before marking it active.
5. Add missing labels or acceptance criteria during triage instead of creating parallel tracking elsewhere.
6. Only sync to `.specs/` when local spec files are part of the work.

## Encoding safety

Treat non-ASCII issue text as a write-path decision, not a cleanup step.

When issue titles or bodies contain Korean or other non-ASCII text:

- Do not create a new issue from shell-escaped inline strings or ad-hoc here-strings.
- Prefer `scripts/issue_manager.py` when it already targets the correct repository and write path.
- Otherwise serialize the JSON payload with explicit UTF-8 before the request.
- If using PowerShell REST calls, send `application/json; charset=utf-8` and use `[System.Text.Encoding]::UTF8.GetBytes($json)` or a UTF-8 file written with `Set-Content -Encoding utf8`.
- Fetch the created or updated issue immediately and confirm the returned title/body before telling the user the write succeeded.
- If verification does not match, treat the first write as failed and retry with the verified UTF-8 payload instead of reporting success and fixing it later.

Preferred sequence:

1. Build the payload object.
2. Serialize it with explicit UTF-8.
3. POST or PATCH once.
4. Read the response back and compare the title/body.
5. Report success only after the comparison passes.

## Triage checklist

- Is this still aligned with the current product direction?
- Should it be `active`, `split`, `defer`, or `close candidate`?
- Does it need labels?
- Does it have scope and acceptance criteria?
- Is it duplicated elsewhere?
- Can it fit in a short side-project session?

## Spec linkage rules

- Do not create a `.specs` document without a GitHub issue number.
- Reuse the issue number in the spec filename.
- Treat epics as containers; keep deliverable work in sub-issues.
- Do not overwrite local spec files with `sync --overwrite` unless the user explicitly wants GitHub to win.

## Safety

- Avoid deleting issues unless the user explicitly asks.
- If an issue looks stale but the decision is unclear, recommend defer or close instead of auto-closing it.
- When triaging an existing backlog, call out unlabeled or oversized issues first.

## Example session

1. Read the active backlog.
2. Group issues into `keep`, `split`, `defer`, and `close candidate`.
3. Rewrite or relabel only the issues that are about to be worked on.
4. Create new issues only after checking for duplicates.
5. Sync `.specs` only if the issue has a corresponding local design doc.
