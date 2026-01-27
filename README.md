# git-rca-workspace

Scaffold and roadmap for the Git RCA Workspace product. This repository will house epics, roadmap, backlog, and code for the MVP.

What I added:
- `EPICS.md` — PMO-style epics with outcomes and acceptance criteria.
- `ROADMAP.md` — high-level milestones and timeline.
- `BACKLOG.md` — top-priority stories for initial sprints.

Next actions I recommend:
1. Paste the text of Issue #2 here or grant access to the GitHub issue so I can validate and enrich the epics to match the original ask.
2. Confirm which epic to prioritize for the MVP (recommended: Core Platform & Data Foundations).
3. I'll decompose chosen epic into stories and create GitHub issues in your repo.

How to run locally (MVP skeleton):

1. Create and activate a virtual environment (optional):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies and run the app:

```bash
pip install -r requirements.txt
python -m src.app
```

3. Run tests:

```bash
pytest -q
```
 
Connector dev notes:
- A simple dev git event connector is available at `src/connectors/git_connector.py` and documented in `docs/git_connector.md`.

Contact the maintainer: repository owner (please ensure repo access for issue creation).
