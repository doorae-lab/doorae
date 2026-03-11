---
name: github-notion-project-ops
description: Use when planning or operating a side project with GitHub issues and Notion only. Splits sources of truth, keeps active work small, and defines a low-overhead weekly and per-session routine.
---

# GitHub + Notion Project Ops

Use this skill when the user wants a practical operating model for a side project that is managed with GitHub and Notion.

## Source of Truth

- GitHub is the execution source of truth.
  - Issues, PRs, labels, milestones, and status live here.
- Notion is the context source of truth.
  - Goals, Now/Next/Later, decision log, and user scenarios live here.
- Do not duplicate issue status in Notion. Link to the GitHub issue instead.

## Default Structure

### Notion

- `Project Home`
  - project goal
  - current constraints
  - repo link
  - top priorities
- `Now / Next / Later`
  - keep `Now` to 1-3 items
- `Decision Log`
  - date
  - decision
  - reason
- `User Scenarios`
  - lightweight product or workflow notes

### GitHub

- Use issues for every actionable task.
- Use epics only as containers for related work.
- Keep labels small and stable. Prefer:
  - `area:*`
  - `priority:*`
  - `small`
  - `blocked`
  - `idea`
  - `stale-candidate`
- Keep milestones limited to real checkpoints such as `MVP` or `v0.1`.

## Operating Loop

### Weekly review

Spend 20-30 minutes to:

1. Move items between `Later`, `Next`, and `Now` in Notion.
2. Choose at most 1-3 active GitHub issues.
3. Close, defer, or relabel stale issues.

### Per work session

1. Open one GitHub issue only.
2. If it will take more than 1-2 sessions, split it before starting.
3. Work on a single branch for that issue.
4. End the session by leaving a short next-step note in the issue or PR.

### Monthly cleanup

1. Remove dead ideas from the active queue.
2. Review unlabeled, duplicate, or stale issues.
3. Move speculative ideas back to Notion `Later` instead of keeping them active in GitHub.

## Triage Rules

- Split issues that mix API, UI, data model, docs, or infra work.
- Rewrite issues that do not have scope or acceptance criteria.
- Keep `Now` small enough that the user can re-enter the project quickly after a busy work week.
- Prefer finishing stability or refactor work already in progress before opening new product surfaces.
- If the backlog mixes current engine work with old product ideas, separate them into `active`, `defer`, and `close candidate` buckets first.

## Writing Rules

### GitHub issue

- one outcome per issue
- short background
- clear scope
- explicit out-of-scope
- acceptance criteria or definition of done

### Notion entry

- keep it short
- store decisions and priority, not duplicated execution state
- link back to GitHub issues instead of copying status text
