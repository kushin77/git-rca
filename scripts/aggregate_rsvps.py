#!/usr/bin/env python3
"""Aggregate RSVP-like replies from created pilot invitation issues.

This script reads `docs/PILOT_INVITE_RESULTS.md` to find target repos and issue URLs,
then queries each issue's comments via the `gh` CLI and extracts comments that
appear to contain RSVPs (simple keyword matching). Results are appended to
`docs/PILOT_RSVP_TEMPLATE.md`.

Run: python3 scripts/aggregate_rsvps.py
"""
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs" / "PILOT_INVITE_RESULTS.md"
RSVP = ROOT / "docs" / "PILOT_RSVP_TEMPLATE.md"


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return p.stdout


def parse_results():
    repos = []
    if not RESULTS.exists():
        return repos
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(kushin77/[A-Za-z0-9_.-]+):", line)
        if m:
            repos.append(m.group(1))
    return repos


def find_issue_number(repo, title):
    out = run(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "100", "--json", "number,title"]) 
    items = json.loads(out)
    for it in items:
        if it.get("title","").strip().lower() == title.strip().lower():
            return it.get("number")
    return None


def list_comments(repo, issue_number):
    out = run(["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "comments"]) 
    data = json.loads(out)
    return data.get("comments", [])


def looks_like_rsvp(text):
    txt = text.lower()
    triggers = ["rsvp", "i'm in", "im in", "count me in", "i'm interested", "yes", "i can", "available", "i'd join", "i will join", "i'll join"]
    for t in triggers:
        if t in txt:
            return True
    return False


def main():
    repos = parse_results()
    if not repos:
        print("No repos found in results file.")
        return
    title = "Pilot Invitation: Investigation Canvas"
    rows = []
    for repo in repos:
        try:
            issue_num = find_issue_number(repo, title)
            if not issue_num:
                continue
            comments = list_comments(repo, issue_num)
            for c in comments:
                body = c.get("body","")
                author = c.get("author", {}).get("login","")
                if looks_like_rsvp(body):
                    rows.append((repo, f"https://github.com/{repo}/issues/{issue_num}", author, body.strip()))
        except Exception as e:
            print(f"{repo}: error {e}")

    if rows:
        txt = RSVP.read_text(encoding="utf-8")
        with RSVP.open("a", encoding="utf-8") as f:
            f.write("\n\n## Aggregated RSVPs\n\n")
            f.write("| Repo | Issue URL | Respondent | Comment |\n")
            f.write("|------|-----------|------------|---------|\n")
            for r in rows:
                f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3].replace('|','\\|')} |\n")
        print(f"Appended {len(rows)} RSVP(s) to {RSVP}")
    else:
        print("No RSVP-like comments found.")


if __name__ == "__main__":
    main()
