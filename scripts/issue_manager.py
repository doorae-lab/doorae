
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

            # Attempt to find Epic from body string "Epic: #106"
            epic_match = re.search(r"Epic: #(\d+)", body)
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

    args = parser.parse_args()

    if args.command == "check":
        asyncio.run(check_issue(args.title))
    elif args.command == "create":
        asyncio.run(create_issue(args.title, args.body))
    elif args.command == "sync":
        asyncio.run(sync_issues(args.overwrite))
