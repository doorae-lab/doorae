
import os
import sys
import argparse
import asyncio
import httpx
import re
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
REPO_OWNER = "yaklevel" # Hardcoded for now based on context, can be parameterized
REPO_NAME = "thetable"

if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN is not set in .env")
    sys.exit(1)

BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

SPECS_DIR = Path(".specs")

async def get_issues(client: httpx.AsyncClient) -> List[Dict]:
    """Fetch all open issues from the repository."""
    issues = []
    page = 1
    while True:
        try:
            response = await client.get(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
                params={"state": "open", "per_page": 100, "page": page}
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            issues.extend(batch)
            page += 1
        except httpx.HTTPStatusError as e:
            print(f"Error fetching issues: {e}")
            sys.exit(1)
    return issues

async def check_issue(title: str):
    """Check if an issue with the given title exists."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        issues = await get_issues(client)
        for issue in issues:
            if issue["title"] == title:
                print(f"✅ Issue already exists: #{issue['number']} {issue['title']}")
                print(f"🔗 URL: {issue['html_url']}")
                return
    print("✨ No existing issue found with this title.")

async def create_issue(title: str, body: str):
    """Create a new issue if it doesn't exist."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        # 1. Check existence first
        issues = await get_issues(client)
        for issue in issues:
            if issue["title"] == title:
                print(f"⚠️ Issue already exists: #{issue['number']} {issue['title']}")
                return

        # 2. Create issue
        payload = {"title": title, "body": body}
        try:
            response = await client.post(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
                json=payload
            )
            response.raise_for_status()
            new_issue = response.json()
            print(f"✅ Issue created: #{new_issue['number']} {new_issue['title']}")
            print(f"🔗 URL: {new_issue['html_url']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to create issue: {e}")
            print(f"Response: {e.response.text}")

async def update_issue(number: int, body: str = None, state: str = None):
    """Update an existing issue."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        payload = {}
        if body:
            payload["body"] = body
        if state:
            payload["state"] = state
            
        if not payload:
            print("⚠️ No changes requested.")
            return

        try:
            response = await client.patch(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{number}",
                json=payload
            )
            response.raise_for_status()
            updated_issue = response.json()
            print(f"✅ Issue updated: #{updated_issue['number']} {updated_issue['title']} (State: {updated_issue['state']})")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to update issue: {e}")
            print(f"Response: {e.response.text}")

async def push_issue(filepath: str):
    """Push local spec file content to GitHub issue."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ File not found: {filepath}")
        return

    # Extract issue number from filename (e.g., 131-*.md -> 131)
    match = re.match(r"^(\d+)-", path.name)
    if not match:
        print(f"❌ Could not extract issue number from filename: {path.name}")
        return
    
    number = int(match.group(1))
    
    # Read file content
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"🚀 Pushing {path.name} to Issue #{number}...")
    await update_issue(number, content)

async def get_issue_details(number: int) -> Optional[Dict]:
    """Fetch details of a specific issue."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{number}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to fetch issue #{number}: {e}")
            return None

async def delete_issue(issue_number: int):
    """Delete an issue using GitHub GraphQL API. (Requires admin/delete_repo permissions)"""
    # First, get the issue's node_id via REST API
    issue = await get_issue_details(issue_number)
    if not issue:
        print(f"❌ Issue #{issue_number} not found.")
        return
    
    node_id = issue["node_id"]
    
    query = """
    mutation DeleteIssue($input: DeleteIssueInput!) {
      deleteIssue(input: $input) {
        clientMutationId
      }
    }
    """
    
    variables = {"input": {"issueId": node_id}}
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/graphql",
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Failed to delete issue #{issue_number}: {data['errors'][0]['message']}")
            else:
                print(f"🗑️ Issue #{issue_number} deleted successfully.")
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to execute GraphQL mutation: {e}")
            print(f"Response: {e.response.text}")

async def create_pr(title: str, body: str, head: str, base: str):
    """Create a new Pull Request."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        try:
            response = await client.post(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
                json=payload
            )
            response.raise_for_status()
            pr = response.json()
            print(f"✅ PR Created: #{pr['number']} {pr['title']}")
            print(f"🔗 URL: {pr['html_url']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to create PR: {e}")
            print(f"Response: {e.response.text}")

async def add_sub_issue(epic_number: int, sub_issue_id: int):
    """Add a sub-issue to an Epic using GitHub Sub-issues API."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        # Use replace_parent=True to handle cases where it might be linked to another Epic (e.g. #107)
        payload = {
            "sub_issue_id": sub_issue_id,
            "replace_parent": True
        }
        try:
            # Note: This endpoint is part of the new Sub-issues API
            response = await client.post(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{epic_number}/sub_issues",
                json=payload
            )
            # 201 Created is expected
            if response.status_code == 201:
                print(f"✅ Linked Sub-issue ID {sub_issue_id} to Epic #{epic_number}")
            elif response.status_code == 422: # Already added or invalid
                 # Sometimes 422 means it is already a sub-issue. We can check response text.
                 # But generally we can ignore if already added?
                 # Let's print warning.
                 print(f"⚠️ Failed to link Sub-issue ID {sub_issue_id} (Maybe already linked?): {response.text}")
            else:
                 response.raise_for_status()
                 
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to add sub-issue: {e}")
            print(f"Response: {e.response.text}")

async def ensure_repo_label(name: str, color: str = "cfd3d7"):
    """Ensure a label exists in the repo with a specific color."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        try:
            response = await client.get(f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/labels/{name}")
            if response.status_code == 200:
                label_data = response.json()
                if label_data.get("color").lower() != color.lower():
                    await client.patch(
                        f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/labels/{name}",
                        json={"color": color}
                    )
                    print(f"🎨 Updated global label '{name}' color to #{color}")
                return
            
            if response.status_code == 404:
                await client.post(
                    f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/labels",
                    json={"name": name, "color": color}
                )
                print(f"🆕 Created global label '{name}' with color #{color}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to manage repo label '{name}': {e}")

async def ensure_label(number: int, label: str):
    """Ensure an issue has a specific label (Epic=Purple, Others=Gray)."""
    # Define colors
    COLOR_PURPLE = "7057ff"
    COLOR_GRAY = "cfd3d7"
    
    # Use purple for epic, gray for everything else
    color = COLOR_PURPLE if label.lower() == "epic" else COLOR_GRAY
    
    # Ensure the label exists in the repo with the correct color
    await ensure_repo_label(label, color)
    
    async with httpx.AsyncClient(headers=HEADERS) as client:
        # Get current labels first
        try:
            response = await client.get(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{number}"
            )
            response.raise_for_status()
            issue = response.json()
            current_labels = [l["name"] for l in issue.get("labels", [])]
            
            if label in current_labels:
                # print(f"✅ Issue #{number} already has label '{label}'")
                return

            # Add label
            new_labels = current_labels + [label]
            payload = {"labels": new_labels}
            
            response = await client.patch(
                f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{number}",
                json=payload
            )
            response.raise_for_status()
            print(f"🏷️ Added label '{label}' to Issue #{number}")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to update labels for issue #{number}: {e}")

def sanitize_filename(title: str) -> str:
    """Sanitize title for filename."""
    # Remove special characters, replace spaces with hyphens
    s = re.sub(r'[^\w\s-]', '', title).strip().lower()
    return re.sub(r'[-\s]+', '-', s)

def find_epic_dir(epic_number: int) -> Optional[Path]:
    """Find the directory corresponding to an epic number."""
    # Look for directories starting with the epic number in .specs/project or .specs/user
    search_paths = [SPECS_DIR / "project", SPECS_DIR / "user"]
    
    for base_path in search_paths:
        if not base_path.exists():
            continue
        for path in base_path.iterdir():
            if path.is_dir() and path.name.startswith(f"{epic_number}-"):
                return path
    return None

async def sync_issues(overwrite: bool = False):
    """Sync issues from GitHub to local .specs directory."""
    print(f"🔄 Syncing issues from GitHub... (Overwrite: {overwrite})")
    async with httpx.AsyncClient(headers=HEADERS) as client:
        issues = await get_issues(client)
        
        # Identify Epics (issues with 'epic' label) - simplified logic for now: assume manual mapping or label
        # Ideally, we look for labels. For now, let's sync all and try to categorize.
        
        epics = {} # id -> title
        
        # 1. First pass: Find Epics
        for issue in issues:
            labels = [l["name"] for l in issue.get("labels", [])]
            if "epic" in labels or "Epic" in labels:
                epics[issue["number"]] = issue["title"]

        # 2. Sync files
        synced_count = 0
        updated_count = 0
        skipped_count = 0
        
        for issue in issues:
            number = issue["number"]
            title = issue["title"]
            body = issue.get("body", "") or ""
            labels = [l["name"] for l in issue.get("labels", [])]
            
            # Skip if it is a pull request
            if "pull_request" in issue:
                continue

            # If it is an Epic, ensure directory exists but SKIP file creation
            if "epic" in labels or "Epic" in labels or "EPIC" in labels:
                epic_dir = find_epic_dir(number)
                sanitized_title = sanitize_filename(title)
                expected_dirname = f"{number}-{sanitized_title}"
                
                if epic_dir:
                    # Rename if necessary
                    if epic_dir.name != expected_dirname:
                        new_path = epic_dir.parent / expected_dirname
                        try:
                            epic_dir.rename(new_path)
                            print(f"📂 Renamed Epic Dir: {epic_dir.name} -> {new_path.name}")
                        except OSError as e:
                            print(f"❌ Failed to rename Epic Dir {epic_dir.name}: {e}")
                else:
                    # Create new directory (default to project for now, or maybe ask? default to project)
                    # Let's put it in .specs/project by default for now
                    new_path = SPECS_DIR / "project" / expected_dirname
                    new_path.mkdir(parents=True, exist_ok=True)
                    print(f"📂 Created Epic Dir: {new_path}")
                
                # Verify no file exists for this Epic
                # If a file like 107-*.md exists, valid to warn or delete? 
                # User said "Epic is folder only". Let's removing existing file if it exists?
                # Maybe too aggressive. Let's just NOT create it.
                continue

            # Attempt to find Epic from body string "Epic: #106"
            epic_match = re.search(r"Epic: #(\d+)", body)
            epic_title_match = re.search(r"Epic: #(\d+)", title) # Sometimes people put it in title? No, body.
            epic_id = int(epic_match.group(1)) if epic_match else None
            
            target_dir = None
            existing_file = None

            # Check if file already exists anywhere to find its current location/name
            # We iterate through all potential files to find one that starts with the number
            for path in SPECS_DIR.rglob("*.md"):
                if path.name.startswith(f"{number}-"):
                    existing_file = path
                    target_dir = path.parent
                    
                    # RENAME if necessary: If existing filename != GitHub title format
                    sanitized_title = sanitize_filename(title)
                    expected_filename = f"{number}-{sanitized_title}.md"
                    
                    if path.name != expected_filename:
                        new_path = target_dir / expected_filename
                        try:
                            path.rename(new_path)
                            print(f"🔄 Renamed: {path.name} -> {new_path.name}")
                            existing_file = new_path
                        except OSError as e:
                            print(f"❌ Failed to rename {path.name}: {e}")
                    break

            # If not found, try to determine target dir
            if not target_dir:
                if epic_id:
                    target_dir = find_epic_dir(epic_id)
                
                # If still no target dir, and it IS an epic, maybe it has its own dir?
                if not target_dir and ("epic" in labels or "Epic" in labels):
                    target_dir = find_epic_dir(number)

            # If still found nothing, skip for now to avoid cluttering root
            if not target_dir:
                # print(f"⚠️ Skipping #{number} {title}: No linking Epic or existing file found.")
                continue

            # Prepare content
            content = f"# {title}\n\n- 이슈: #{number}\n"
            if epic_id:
                content += f"- Epic: #{epic_id}\n"
            content += f"- 상태: {issue['state']}\n"
            content += f"- 작성일: {issue['created_at'][:10]}\n\n"
            content += body

            if existing_file:
                if overwrite:
                     print(f"⚠️ Overwriting content: {existing_file}")
                     with open(existing_file, "w", encoding="utf-8") as f:
                        f.write(content)
                     updated_count += 1
                else:
                    skipped_count += 1
            else:
                # Determine filename for new file
                sanitized_title = sanitize_filename(title)
                filename = f"{number}-{sanitized_title}.md"
                filepath = target_dir / filename
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Created: {filepath}")
                synced_count += 1

        print(f"✨ Sync complete. Created: {synced_count}, Updated: {updated_count}, Skipped: {skipped_count}")

async def push_all():
    """Push all local specs to GitHub and ensure Epics exist with labels."""
    print("🚀 Pushing ALL specs to GitHub...")
    
    # 1. Scan Directories (Epics)
    # Search all top-level directories under .specs (e.g., project, user, agent, infra, meeting, interface)
    for path in SPECS_DIR.iterdir():
        if path.is_dir():
             base_path = path
             for sub_path in base_path.iterdir():
                 if sub_path.is_dir():
                     # Check if it follows NNN-Title format
                     match = re.match(r"^(\d+)-", sub_path.name)
                     if match:
                         epic_number = int(match.group(1))
                         # Ensure Epic Label
                         await ensure_label(epic_number, "epic")
                         
                         # Ensure Category Label (e.g., "project", "user", "agent")
                         category_label = base_path.name
                         await ensure_label(epic_number, category_label)
                         
                         # Link Sub-issues
                         # Scan directory for child specs
                         for spec_path in sub_path.glob("*.md"):
                              spec_match = re.match(r"^(\d+)-", spec_path.name)
                              if spec_match:
                                  sub_number = int(spec_match.group(1))
                                  # Get Sub-issue Details (to get internal ID)
                                  sub_issue = await get_issue_details(sub_number)
                                  if sub_issue:
                                      await add_sub_issue(epic_number, sub_issue["id"])
                                  else:
                                      print(f"⚠️ Could not fetch details for sub-issue #{sub_number}")
    
    # 2. Scan Files (Specs)
    for path in SPECS_DIR.rglob("*.md"):
        await push_issue(str(path))
    
    print("✨ Push All complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage GitHub issues for specs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Check command
    check_parser = subparsers.add_parser("check", help="Check if an issue exists")
    check_parser.add_argument("--title", required=True, help="Issue title")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new issue")
    create_parser.add_argument("--title", required=True, help="Issue title")
    create_parser.add_argument("--body", required=False, default="", help="Issue body")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync issues to local specs")
    sync_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update an issue body or state")
    update_parser.add_argument("--number", required=True, type=int, help="Issue number")
    update_parser.add_argument("--body", required=False, help="New issue body")
    update_parser.add_argument("--state", required=False, choices=["open", "closed"], help="New issue state")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an issue (Requires Admin/GraphQL)")
    delete_parser.add_argument("--number", required=True, type=int, help="Issue number")

    # PR command
    pr_parser = subparsers.add_parser("create-pr", help="Create a Pull Request")
    pr_parser.add_argument("--title", required=True, help="PR title")
    pr_parser.add_argument("--body", required=False, default="", help="PR body")
    pr_parser.add_argument("--head", required=True, help="Source branch (e.g., develop)")
    pr_parser.add_argument("--base", required=True, help="Target branch (e.g., main)")

    # Push command
    push_parser = subparsers.add_parser("push", help="Push local spec file to GitHub")
    push_parser.add_argument("file", nargs="?", help="Path to the local spec file (optional if push-all)") # Modified logic implicitly? No, separate command better
    
    # push-all command
    subparsers.add_parser("push-all", help="Push ALL local specs and sync Epics")

    args = parser.parse_args()

    if args.command == "check":
        asyncio.run(check_issue(args.title))
    elif args.command == "create":
        asyncio.run(create_issue(args.title, args.body))
    elif args.command == "sync":
        asyncio.run(sync_issues(args.overwrite))
    elif args.command == "update":
        asyncio.run(update_issue(args.number, args.body, args.state))
    elif args.command == "delete":
        asyncio.run(delete_issue(args.number))
    elif args.command == "create-pr":
        asyncio.run(create_pr(args.title, args.body, args.head, args.base))
    elif args.command == "push":
        if args.file:
             asyncio.run(push_issue(args.file))
        else:
             print("Error: file path required for 'push'. Use 'push-all' for everything.")
    elif args.command == "push-all":
        asyncio.run(push_all())
