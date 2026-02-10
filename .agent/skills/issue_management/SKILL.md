---
name: Issue Management
description: Manage GitHub issues (check, create, sync) using a local Python script.
---

# Issue Management Skill

This skill allows the agent to manage GitHub issues directly from the command line using the `scripts/issue_manager.py` script.

## Capabilities

1.  **Check Issue**: Verify if an issue with a specific title already exists.
2.  **Create Issue**: Create a new issue on GitHub.
3.  **Sync Issues**: Fetch all open issues and sync them to the local `.specs` directory.

## Prerequisites

- `GITHUB_TOKEN` or `GITHUB_PERSONAL_ACCESS_TOKEN` must be set in `.env`.
- `httpx` must be installed (`pip install httpx`).

## Usage

### 1. Check if an issue exists

Before creating a new issue, always check if it already exists to avoid duplicates.

```bash
python scripts/issue_manager.py check --title "Issue Title"
```

### 2. Create a new issue

If the issue does not exist, create it.

```bash
python scripts/issue_manager.py create --title "Issue Title" --body "Detailed description..."
```

**Note**: The script will double-check for existence before creating.

### 3. Sync issues

Pull all open issues from GitHub and update the local `.specs` directory.

```bash
python scripts/issue_manager.py sync
```

To **overwrite** existing local files with GitHub content (useful if you want to reset to the GitHub state), use:

```bash
python scripts/issue_manager.py sync --overwrite
```

- **Logic**:
    - The script fetches all open issues.
    - It attempts to map issues to existing Epic directories (based on `Epic: #ID` in the body or existing directory names).
    - If a matching file exists (by issue number):
        - Default: **Skips** overwriting to preserve local changes.
        - With `--overwrite`: **Overwrites** the file content with the GitHub issue body.
    - If a file does not exist, it creates a new one with the issue content.

## Example Workflow

1.  **User Request**: "Add a login screen feature."
2.  **Check**: `python scripts/issue_manager.py check --title "Login Screen"`
    - Output: `✨ No existing issue found...`
3.  **Create**: `python scripts/issue_manager.py create --title "Login Screen" --body "Implement login UI..."`
    - Output: `✅ Issue created: #115 Login Screen`
4.  **Sync**: `python scripts/issue_manager.py sync`
    - Output: `✅ Created: .specs/user/106-user-management/115-login-screen.md`
