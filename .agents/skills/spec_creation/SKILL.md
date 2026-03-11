---
name: spec-creation
description: Use when creating or reorganizing `.specs` files in this repository. Keeps specs aligned with GitHub issue numbers, epic folders, and the current area-based directory layout.
---

# Spec Creation Skill

Use this skill for local design or planning documents under `.specs/`.

## Preferred layout

```text
.specs/<area>/<epic-number>-<epic-title>/<issue-number>-<issue-title>.md
```

Current top-level areas in this repository:

- `agent`
- `infra`
- `interface`
- `meeting`
- `project`
- `user`

Use the GitHub issue number when one exists. Keep the rest of the filename human-readable and close to the GitHub title.

## Required workflow

1. Check GitHub first. Use the `issue-management` skill if the issue does not exist yet.
2. Reuse the GitHub issue number in the local spec filename.
3. Put the spec inside the matching epic directory when one exists.
4. If a file already exists for that issue number, update or rename it instead of creating a duplicate.
5. Preserve the current area-based layout unless the user asks for a broader reorganization.

## Templates

### Sub-issue spec

```markdown
# <Title>

- Issue: #131
- Epic: #134 Project Management
- Status: draft
- Created: 2026-03-08

## Overview
<one paragraph summary>

## Scope
- [ ] item

## Out of Scope
- item

## Acceptance Criteria
- [ ] item

## Related Code
- `path/to/file`
```

### Epic directory note

When an epic is represented as a directory, use `__init__.md` only if you need local context that is not already captured in the GitHub epic body.

## Cleanup rules

- Keep one spec file per GitHub issue number.
- Rename files when the GitHub title changes enough to justify cleanup.
- Normalize duplicate spellings, case variants, or old naming styles instead of adding new files.
- If a spec no longer maps to an active issue, flag it for review before deleting.

## Review checklist

- Does the file map to a real GitHub issue?
- Is it in the right area folder?
- Is there an existing file for the same issue number?
- Does the header show issue, epic, status, and created date?
- Are scope and acceptance criteria concrete enough to implement?
