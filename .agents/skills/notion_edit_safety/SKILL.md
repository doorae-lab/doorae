---
name: Notion Edit Safety
description: Preserve existing links when editing Notion pages. Use for any request that updates Notion page content so edits are based on the current source and do not accidentally remove previously written links.
---

# Notion Edit Safety Skill

Apply this workflow for every Notion content update.

## Required Workflow

1. Fetch the current page first.
2. Read the full current content and identify existing links before editing.
3. Prefer partial edits over full replacement:
   - First choice: `replace_content_range`
   - Second choice: `insert_content_after`
   - Last resort: `replace_content` only when explicitly required
4. When full replacement is required, merge old links into the new draft unless the user explicitly asks to remove them.
5. Update the page.
6. Fetch the page again and verify link preservation.
7. If links were removed unintentionally, fix immediately with a follow-up content update.

## Link Preservation Checklist

Before update, record links found in source content:
- Standard links: `[text](https://...)`
- Raw URLs: `https://...`
- Notion entity links in tags (for example `url="https://www.notion.so/..."`)
- Important references the user previously added

After update:
- Compare pre-update and post-update link sets.
- Confirm that all previously existing links are still present unless the user asked for deletion.
- Report in the final response that source was checked and links were preserved.

## Response Rule

When reporting completion of a Notion edit, include:
- Confirmation that original content was fetched first
- Whether edit was partial or full replacement
- Confirmation that existing links were preserved (or explicit note of intentional removals)
