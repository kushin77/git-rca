#!/usr/bin/env python3
"""Create canonical issues and milestones in a GitHub repo using a manifest.

Usage:
  GITHUB_TOKEN=ghp_xxx python3 scripts/github_issue_manager.py --owner kushin77 --repo git-rca

This script creates missing labels, milestones, and issues defined in ../issues_to_create.json.
It will skip issues that already exist by title.
"""

import os
import sys
import json
import argparse
import requests


def gh_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def ensure_label(session, base_url, label, color="ededed", description=""):
    url = f"{base_url}/labels/{label}"
    r = session.get(url)
    if r.status_code == 200:
        return True
    create_url = f"{base_url}/labels"
    payload = {"name": label, "color": color, "description": description}
    r = session.post(create_url, json=payload)
    return r.status_code in (200, 201)


def get_milestones(session, base_url):
    url = f"{base_url}/milestones?state=all"
    r = session.get(url)
    r.raise_for_status()
    return {m["title"]: m for m in r.json()}


def create_milestone(session, base_url, title, description=""):
    url = f"{base_url}/milestones"
    payload = {"title": title, "description": description}
    r = session.post(url, json=payload)
    r.raise_for_status()
    return r.json()


def issue_exists(session, base_url, title):
    # Search issues by title via list issues (filter by state=all)
    url = f"{base_url}/issues?state=all&per_page=100"
    r = session.get(url)
    r.raise_for_status()
    for it in r.json():
        if it.get("title", "") == title:
            return True, it
    return False, None


def create_issue(session, base_url, issue, milestone_number=None):
    url = f"{base_url}/issues"
    payload = {
        "title": issue["title"],
        "body": issue.get("body", ""),
        "labels": issue.get("labels", []),
    }
    if issue.get("assignees"):
        payload["assignees"] = issue.get("assignees")
    if milestone_number:
        payload["milestone"] = milestone_number
    r = session.post(url, json=payload)
    r.raise_for_status()
    return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--manifest", default="issues_to_create.json")
    args = p.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable required", file=sys.stderr)
        sys.exit(1)

    with open(args.manifest) as f:
        manifest = json.load(f)

    base_url = f"https://api.github.com/repos/{args.owner}/{args.repo}"
    session = requests.Session()
    session.headers.update(gh_headers(token))

    # Ensure labels
    all_labels = set()
    for issue in manifest.get("issues", []):
        for lab in issue.get("labels", []):
            all_labels.add(lab)

    for lab in sorted(all_labels):
        ok = ensure_label(session, base_url, lab)
        print(f"label: {lab} -> {'ok' if ok else 'fail'}")

    # Ensure milestones
    existing_milestones = get_milestones(session, base_url)
    milestone_map = {}
    for ms in manifest.get("milestones", []):
        title = ms["title"]
        if title in existing_milestones:
            milestone_map[title] = existing_milestones[title]["number"]
            continue
        m = create_milestone(session, base_url, title, ms.get("description", ""))
        milestone_map[title] = m["number"]
        print(f"created milestone: {title}")

    # Create issues
    for issue in manifest.get("issues", []):
        title = issue["title"]
        exists, existing = issue_exists(session, base_url, title)
        if exists:
            print(f"skipping existing issue: {title} -> {existing.get('html_url')}")
            continue
        ms_num = None
        if issue.get("milestone"):
            ms_num = milestone_map.get(issue["milestone"])
        created = create_issue(session, base_url, issue, milestone_number=ms_num)
        print(f"created issue: {created.get('title')} -> {created.get('html_url')}")


if __name__ == "__main__":
    main()
