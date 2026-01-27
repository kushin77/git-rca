# git-rca-workspace

Scaffold and roadmap for the Git RCA Workspace product. This repository will house epics, roadmap, backlog, code, and docs for the MVP.

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

## Project Status

**Completed Epics & Stories:**
- [x] Epics 1-7: PMO-style epics defined
- [x] Epic: Core Platform & Architecture (closed)
- [x] Epic: Data & Integrations (closed)  
- [x] Epic: RCA Workflow & UX (design phase — mockups created)
- [x] Epic: Security, Compliance & Privacy (threat model created)

**In Progress:**
- [ ] Investigation Canvas UI Prototype (Story #16)
- [ ] Investigations Data Model & API (Story #17)
- [ ] Event Linking & Annotations (Story #18)
- [ ] Pilot Validation & Feedback (Story #19)

**Documentation:**
- `docs/ux_mockups.md` — investigation canvas mockups
- `docs/investigation_stories.md` — breakdown of canvas implementation stories
- `docs/security_threat_model.md` — baseline threat model and recommendations
- `docs/ARCHITECTURE.md` — core platform architecture overview
- `docs/connectors_hardening.md` — connector validation and retry logic
- `docs/schema.md` — event schema for MVP
- `docs/api_events.md` — events query API with filters
- `docs/git_connector.md` and `docs/ci_connector.md` — connector documentation

## Quick Links

- [Epics](EPICS.md)
- [Roadmap](ROADMAP.md)
- [Backlog](BACKLOG.md)
- [Contributing](CONTRIBUTING.md)
- [License](LICENSE)
