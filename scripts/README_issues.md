# Creating canonical issues and milestones

This folder contains an automation script to create the canonical P0/P1 issues and milestones defined in `issues_to_create.json`.

Usage (recommended):

```bash
# Export a GitHub token with repo access
export GITHUB_TOKEN=ghp_xxx
python3 scripts/github_issue_manager.py --owner kushin77 --repo git-rca
```

What it does:
- Creates any missing labels used in the manifest
- Creates milestones if not present
- Creates issues from the manifest and skips duplicates by title

Permissions: `GITHUB_TOKEN` must have `repo` scope to create issues/milestones/labels.

Next steps after creating issues:
- Review and assign owners
- Create a Project board and map epics → milestones (can be done via `gh` CLI or GitHub UI)
