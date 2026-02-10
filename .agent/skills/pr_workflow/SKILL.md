---
name: Pull Request Workflow
description: Automates the process of creating a pull request using the custom issue_manager script, replacing the need for gh CLI.
---

# Pull Request Workflow Skill

This skill allows you to create GitHub Pull Requests using the local `scripts/issue_manager.py` script, which directly interacts with the GitHub API. This is useful when the `gh` CLI is not available.

## Prerequisites

- **Python Environment**: `httpx` and `python-dotenv` must be installed.
- **Environment Variables**: `GITHUB_TOKEN` must be set in `.env`.
- **Script**: `scripts/issue_manager.py` must contain the `create-pr` command.

## Usage

### Create a Pull Request

To create a Pull Request from a source branch (e.g., `develop`) to a target branch (e.g., `main`):

```bash
python scripts/issue_manager.py create-pr \
  --title "PR Title" \
  --body "Detailed description of the changes" \
  --head <source_branch> \
  --base <target_branch>
```

### Example

```bash
python scripts/issue_manager.py create-pr \
  --title "CHORE: Refactor Specs" \
  --body "Consolidates specs and updates sync logic." \
  --head develop \
  --base main
```
