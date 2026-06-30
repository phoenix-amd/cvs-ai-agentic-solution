#!/usr/bin/env python3
"""
CVS AI Agentic Solution — Self-Update Version Checker

Checks the local version against the latest GitHub release.
Offers to update if a newer version is available.

Usage:
    python3 version_check.py                    # check for updates
    python3 version_check.py --update           # update to latest
    python3 version_check.py --current          # show current version
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/phoenix-amd/cvs-ai-agentic-solution"
VERSION_FILE = Path(__file__).parent.parent / "version.txt"
CHANGELOG = Path(__file__).parent.parent / "CHANGELOG.md"


def get_local_version() -> str:
    """Get current local version from version.txt."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    # Fallback: parse from CHANGELOG
    if CHANGELOG.exists():
        for line in CHANGELOG.read_text().splitlines():
            if line.startswith("## ["):
                ver = line.split("[")[1].split("]")[0]
                return ver
    return "unknown"


def get_remote_version() -> dict:
    """Check GitHub for latest version via git ls-remote tags."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--sort=-v:refname", REPO_URL],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"version": "unknown", "error": result.stderr.strip()}

        tags = []
        for line in result.stdout.strip().splitlines():
            if "refs/tags/v" in line and "^{}" not in line:
                tag = line.split("refs/tags/")[1]
                tags.append(tag)

        if tags:
            latest = tags[0]  # already sorted by version
            return {"version": latest.lstrip("v"), "tag": latest}
        return {"version": "unknown", "error": "No tags found"}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}


def update_to_latest() -> bool:
    """Pull latest changes from GitHub."""
    try:
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_root, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"Updated successfully: {result.stdout.strip()}")
            return True
        else:
            print(f"Update failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Update error: {e}")
        return False


def check_version() -> dict:
    """Compare local and remote versions."""
    local = get_local_version()
    remote = get_remote_version()

    result = {
        "local_version": local,
        "remote_version": remote.get("version", "unknown"),
        "update_available": False,
        "error": remote.get("error"),
    }

    if local != "unknown" and remote["version"] != "unknown":
        # Simple version comparison
        local_parts = [int(x) for x in local.split(".") if x.isdigit()]
        remote_parts = [int(x) for x in remote["version"].split(".") if x.isdigit()]
        result["update_available"] = remote_parts > local_parts

    return result


def main():
    parser = argparse.ArgumentParser(description="CVS AI Agentic Solution Version Checker")
    parser.add_argument("--current", action="store_true", help="Show current version")
    parser.add_argument("--check", action="store_true", help="Check for updates")
    parser.add_argument("--update", action="store_true", help="Update to latest version")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.current:
        ver = get_local_version()
        if args.json:
            print(json.dumps({"version": ver}))
        else:
            print(f"CVS AI Agentic Solution v{ver}")
        return

    if args.update:
        info = check_version()
        if info["update_available"]:
            print(f"Updating from v{info['local_version']} to v{info['remote_version']}...")
            if update_to_latest():
                # Update version.txt
                VERSION_FILE.write_text(info["remote_version"] + "\n")
                print("Update complete.")
            else:
                print("Update failed. Try: git pull origin main")
        else:
            print(f"Already at latest version: v{info['local_version']}")
        return

    # Default: check
    info = check_version()
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Local:  v{info['local_version']}")
        print(f"Remote: v{info['remote_version']}")
        if info.get("error"):
            print(f"Note:   {info['error']}")
        if info["update_available"]:
            print(f"\nUpdate available! Run: python3 tools/version_check.py --update")
        else:
            print(f"\nYou are up to date.")


if __name__ == "__main__":
    main()
