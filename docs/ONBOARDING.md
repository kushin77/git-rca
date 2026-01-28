```markdown
# Pilot Onboarding Guide

Purpose: Provide a compact, actionable onboarding checklist for pilot engineers to get the Git RCA Workspace running and start a first RCA.

Prereqs
- Git, Python 3.10+, Docker (optional for sandbox)

Local quickstart
1. Clone the repo: `git clone https://github.com/kushin77/git-rca.git`
2. Create and activate a venv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python -m src.app
   # Open http://localhost:8080 and /api/events
   ```
4. Run tests:
   ```bash
   pytest -q
   ```

Dev sandbox (Docker):
```bash
docker-compose -f infra/docker-compose.yml up --build
```

Pilot workflow (first RCA)
1. Ingest sample git/CI events (see `scripts/generate_ics_from_rsvp.py` and `src/connectors/*`).
2. Use `/api/events` to validate events are stored and queryable.
3. Open the Investigation Canvas prototype (see `docs/ux_mockups.md`) and map events to a timeline.
4. Add annotations and conclusions, then export/share the RCA.

Pilot comms and invites
- See `docs/PILOT_SAMPLE_INVITES.md`, `docs/PILOT_RSVP_TEMPLATE.md`, and `docs/PILOT_CALENDAR_INVITES.md` for email and calendar templates to invite pilot engineers.

Onboarding checklist (ticklist)
- [ ] Environment set up and tests pass
- [ ] Events ingested and queryable
- [ ] Canvas prototype validated by 2 engineers
- [ ] Feedback recorded in `docs/PILOT_FEEDBACK_SUMMARY.md`

Troubleshooting
- DB errors: check `src/store/sql_store.py` and ensure SQLite file writable.
- Missing dependencies: run `pip install -r requirements.txt` and retry.

Owner: Adoption, Docs & Enablement epic

References
- `BACKLOG.md` (pilot onboarding story)
- `docs/ux_mockups.md`, `docs/schema.md`, `docs/connectors_hardening.md`

``` 
