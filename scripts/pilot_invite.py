#!/usr/bin/env python3
"""
Idempotent pilot invitation script using the `gh` CLI.

Usage examples:
  python scripts/pilot_invite.py --org kushin77 --title "Pilot Invitation: Investigation Canvas" --body-file docs/PILOT_INVITE_COPY.md --dry-run
  python scripts/pilot_invite.py --repos kushin77/git-rca-workspace,kushin77/GCP-landing-zone --title "Pilot Invitation" --body "Please join our pilot..."

This script is intentionally conservative: it will not create duplicate issues with the same title.
Requires the `gh` CLI to be authenticated and installed in PATH.
"""
import argparse
import json
import subprocess
import sys
from typing import List


def run(cmd: List[str]) -> str:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr}")
    return proc.stdout


def repo_list_from_org(org: str) -> List[str]:
    out = run(["gh", "repo", "list", org, "--limit", "1000", "--json", "name,owner,isArchived"])
    data = json.loads(out)
    repos = []
    for r in data:
        if not r.get("isArchived", False):
            repos.append(f"{r['owner']['login']}/{r['name']}")
    return repos


def issue_exists(repo: str, title: str) -> bool:
    out = run(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "100", "--json", "title"]) 
    items = json.loads(out)
    for it in items:
        if it.get("title", "").strip().lower() == title.strip().lower():
            return True
    return False


def create_issue(repo: str, title: str, body: str, labels: List[str], dry_run: bool) -> str:
    if issue_exists(repo, title):
        return f"skipped: existing issue in {repo}"
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    if labels:
        cmd += ["--label", ",".join(labels)]
    if dry_run:
        return f"dry-run: would create issue in {repo}"
    out = run(cmd)
    return out.strip()


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--org", help="Organization or user to enumerate repos from")
    p.add_argument("--repos", help="Comma-separated list of repos (owner/repo)")
    p.add_argument("--title", required=True, help="Issue title to create")
    p.add_argument("--body", help="Issue body text (mutually exclusive with --body-file)")
    p.add_argument("--body-file", help="Path to file with issue body")
    p.add_argument("--label", action="append", dest="labels", help="Labels to add to created issues")
    p.add_argument("--dry-run", action="store_true", help="Do not create issues; only show actions")
    args = p.parse_args()

    if not args.body and not args.body_file:
        print("Either --body or --body-file is required", file=sys.stderr)
        sys.exit(2)

    body = args.body or read_file(args.body_file)

    repos = []
    if args.repos:
        repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    elif args.org:
        repos = repo_list_from_org(args.org)
    else:
        print("Either --org or --repos must be provided", file=sys.stderr)
        sys.exit(2)

    results = {}
    for repo in repos:
        try:
            res = create_issue(repo, args.title, body, args.labels or [], args.dry_run)
            results[repo] = res
            print(f"{repo}: {res}")
        except Exception as e:
            results[repo] = f"error: {e}"
            print(f"{repo}: error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
