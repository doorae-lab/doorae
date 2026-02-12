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

## Workflow Rules (Critical)

When adding a new feature or specification:

1.  **ALWAYS Check GitHub First**: Before creating a local spec file, check if a relevant GitHub issue already exists.
    -   If exists: Use the existing **Issue Number** for the spec filename (e.g., `151-meeting-persistence.md`).
    -   If NOT exists: **Create the GitHub Issue FIRST**. Use the generated Issue Number for the spec filename.
2.  **Never create a spec without an issue**: Every spec file must correspond to a GitHub issue.

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
    - **Epics**: If an issue has the `epic` label, it ensures a **directory** exists (e.g., `107-프로젝트-기능`) and skips file creation. content is NOT synced to a file.
    - **Specs (Sub-issues)**: If an issue refers to an Epic (e.g., `Epic: #107` in body), it is saved as a **markdown file** inside that Epic's directory.
    - **File Naming**: Local filenames are automatically renamed to match the GitHub issue title (prioritizing GitHub).
    - If a matching file exists (by issue number):
        - Default: **Skips** overwriting.
        - With `--overwrite`: **Overwrites** content with GitHub issue body.
    - If a file does not exist, it creates a new one with the issue content.

### 4. Push Specs to GitHub

Update existing GitHub issues with the current content of local spec files.

**Single File:**
```bash
python scripts/issue_manager.py push .specs/project/131-프로젝트-관리.md
```

**Sync All (Local -> GitHub):**
```bash
python scripts/issue_manager.py push-all
```

- **Logic**:
    - **`push <file>`**: Updates the body of the corresponding GitHub issue (based on filename ID) with the file content.
    - **`push-all`**:
        - Scans all directories in `.specs`:
            - Ensures the corresponding Epic issue exists and has the `epic` label.
            - **Links sub-issues** using GitHub's native Sub-issues API (`POST /issues/{id}/sub_issues`).
        - Scans all `.md` files: Pushes their content to the corresponding GitHub issues.

1.  **User Request**: "Add a login screen feature."
2.  **Check**: `python scripts/issue_manager.py check --title "Login Screen"`
    - Output: `✨ No existing issue found...`
3.  **Create**: `python scripts/issue_manager.py create --title "Login Screen" --body "Implement login UI..."`
    - Output: `✅ Issue created: #115 Login Screen`
4.  **Sync**: `python scripts/issue_manager.py sync`
    - Output: `✅ Created: .specs/user/106-user-management/115-login-screen.md`
