---
name: github-workflow
description: Use when turning local work into a GitHub-backed change in this repository. Covers branch creation, issue linkage, push, and PR creation using local git plus scripts/issue_manager.py or direct GitHub API access.
---

# GitHub Workflow

Use this skill when the user wants to move local work through the repository workflow.

## Primary path

1. Inspect repo context.
2. Create or reuse a GitHub issue.
3. Create a branch.
4. Make the change.
5. Commit and push.
6. Open a PR linked to the issue.

## Tools

- local `git`
- `scripts/issue_manager.py`
- direct GitHub REST calls when the script does not expose the action

Do not assume GitHub MCP is available.

## Repository checks

Before starting:

- confirm the remote with `git remote -v`
- confirm the current branch and base branch
- check for unrelated dirty changes before committing
- prefer non-interactive git commands only

## Branch rules

- one issue per branch
- use descriptive names
- keep branches short-lived
- do not mix multiple unrelated fixes into one PR

## Issue linkage rules

- check for an existing issue before creating a new one
- use the issue number in commit or PR context when useful
- use `Closes #<issue_number>` in the PR body when the change should close the issue

## Issue write path

When creating or updating an issue with Korean or other non-ASCII text:

1. Choose a UTF-8-safe write path before the first POST or PATCH.
2. Prefer `scripts/issue_manager.py` only when it targets the correct repository for this workspace.
3. Otherwise serialize the REST payload as explicit UTF-8 bytes or a UTF-8 JSON file, then send it once.
4. Read the response back and confirm the returned title/body before reporting success.
5. Do not create mojibake first and plan to fix it afterward.

## PR creation path

Preferred order:

1. `git checkout -b <branch>`
2. `git add <files>`
3. `git commit -m "<message>"`
4. `git push -u origin <branch>`
5. create the PR with `scripts/issue_manager.py create-pr` or direct REST if needed

## Safety

- do not create a PR before the branch exists remotely
- do not assume `main` blindly; inspect the repo first
- if the issue title/body contains Korean or other non-ASCII text, follow the UTF-8-safe write rules from `issue-management` before creating the issue
- if the user only asked for issue work, do not create a PR automatically

## Example

```bash
git checkout -b codex/doorae-cli-entrypoint
git add pyproject.toml thetable/interfaces/cli.py
git commit -m "Add doorae CLI entrypoint"
git push -u origin codex/doorae-cli-entrypoint
python scripts/issue_manager.py create-pr \
  --title "Add doorae CLI entrypoint" \
  --body "Closes #204\n\nAdd the doorae entrypoint and restructure CLI commands." \
  --head codex/doorae-cli-entrypoint \
  --base main
```
