---
description: Submit contribution (Issue -> Branch -> Commit -> Push -> PR)
---

# Submit Contribution Workflow

This workflow automates the process of submitting changes to the repository.

1.  **Create/Check Issue**
    -   Ensure there is a GitHub issue for the task.
    -   If not, create one:
        ```bash
        python scripts/issue_manager.py create --title "<Issue Title>" --body "<Description>"
        ```
    -   Note the Issue Number.

2.  **Check/Create Branch**
    -   Check current branch:
        ```bash
        git branch --show-current
        ```
    -   If on `main` or `develop`, create a new branch:
        ```bash
        git checkout -b feat/issue-<issue_number>-<short-desc>
        ```
    -   If already on a feature branch, ensure it matches the task.

3.  **Commit Changes**
    -   Stage files:
        ```bash
        git add .
        ```
    -   Commit (reference the issue number):
        ```bash
        git commit -m "feat: <Commit Message> (#<issue_number>)"
        ```

4.  **Push Branch**
    -   Push to origin:
        ```bash
        git push origin <branch_name>
        ```

5.  **Create Pull Request**
    -   Create the PR:
        ```bash
        python scripts/issue_manager.py create-pr \
          --title "<PR Title>" \
          --body "Closes #<issue_number>" \
          --head <branch_name> \
          --base main
        ```
