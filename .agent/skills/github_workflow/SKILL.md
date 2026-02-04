---
name: GitHub Workflow
description: Automates the process of creating a feature branch, pushing changes, creating an issue, and opening a linked pull request using GitHub MCP tools.
---

# GitHub Workflow Skill

This skill guides you through the standard development workflow: creating a branch, pushing changes, creating a tracking issue, and opening a pull request linked to that issue.

## Prerequisites

- **GitHub MCP Server** must be active and authenticated.
- **Git CLI** must be configured locally.
- You must be inside a git repository.

## Workflow Steps

### 1. Identify Context

Before starting, determine the following:
- **Repository Name**: Check `config/agent_profiles.yaml` (metadata.target_repository) or run `git remote get-url origin` to parse `owner/repo`.
- **Base Branch**: Usually `main` or `master`. Check `git branch -r | grep HEAD`.
- **Feature Branch Name**: Generate a concise, descriptive name (e.g., `feat/agenda-extraction`, `fix/mcp-connection`).

### 2. Local Git Operations

1.  **Create and Switch to Branch**:
    ```bash
    git checkout -b <branch_name>
    ```
2.  **Stage and Commit Changes** (if not already done):
    ```bash
    git add .
    git commit -m "<descriptive commit message>"
    ```
3.  **Push Branch**:
    ```bash
    git push -u origin <branch_name>
    ```

### 3. Create GitHub Issue

Use the **GitHub MCP tool** `create_issue` to track the work.

- **Tool**: `github.create_issue` (or `create_issue` depending on client context)
- **Arguments**:
  - `owner`: Repository owner
  - `repo`: Repository name
  - `title`: Concise summary of the work
  - `body`: Detailed description of changes, context, and goals.

**IMPORTANT**: Note the **Issue Number** returned by this tool (e.g., `15`).

### 4. Create Pull Request

Use the **GitHub MCP tool** `create_pull_request` to submit the changes.

- **Tool**: `github.create_pull_request`
- **Arguments**:
  - `owner`: Repository owner
  - `repo`: Repository name
  - `title`: Same as issue title or slightly more technical
  - `body`:
    ```markdown
    Closes #<issue_number>
    
    ## Description
    <Brief summary of changes>
    ```
  - `head`: `<branch_name>` (The branch you just pushed)
  - `base`: `main` (or the target base branch)

## Example Usage

```python
# 1. Push local branch
run_command("git checkout -b feat/new-feature && git push -u origin feat/new-feature")

# 2. Create Issue
issue = await mcp_client.call_tool("github", "create_issue", {
    "owner": "yaklevel",
    "repo": "thetable",
    "title": "Add New Feature",
    "body": "Implementing specific functionality..."
})
issue_number = issue.number

# 3. Create PR
await mcp_client.call_tool("github", "create_pull_request", {
    "owner": "yaklevel",
    "repo": "thetable",
    "title": "Add New Feature",
    "body": f"Closes #{issue_number}\n\nImplementation details...",
    "head": "feat/new-feature",
    "base": "main"
})
```
