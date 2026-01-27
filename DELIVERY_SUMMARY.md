# Git RCA Workspace - MVP Delivery Summary

**Date:** January 27, 2026

## Project Overview

The Git RCA Workspace is a root-cause-analysis (RCA) platform designed to help engineering teams investigate and document incidents by correlating events from git, CI/monitoring systems, and logs.

## Completed Work (MVP Scope)

### 1. Elite PMO-Style Epics & Roadmap ✅
- **7 Epics** defined with outcomes, success metrics, stakeholders, and dependencies:
  1. Product Vision & Governance
  2. Core Platform & Architecture *(closed)*
  3. Data & Integrations *(closed)*
  4. RCA Workflow & UX *(design phase)*
  5. Observability, Telemetry & Analytics
  6. Security, Compliance & Privacy
  7. Adoption, Docs & Enablement

- **6-month roadmap** with monthly milestones.
- **Backlog** with prioritized user stories.

### 2. Core Platform & Infrastructure ✅
- **Flask MVP skeleton** with minimal routes (`/`, `/api/events`).
- **CI/CD pipeline** (GitHub Actions) runs tests on push/PR.
- **Dev sandbox** with Dockerfile and docker-compose for local development.
- **Repository structure:** monorepo with `src/`, `tests/`, `docs/`, `infra/`.
- **Contributing guide, LICENSE, .gitignore, architecture overview.**

### 3. Data Layer & Connectors ✅
- **Git Event Connector** (`src/connectors/git_connector.py`) — dev file-backed + SQL insert.
- **CI/Monitoring Connector** (`src/connectors/ci_connector.py`) — dev file-backed + SQL insert.
- **SQLite-backed event store** (`src/store/sql_store.py`) with insert, query, clear.
- **Event validator** (`src/connectors/validator.py`) — accepts events with required fields.
- **Retry decorator** (`src/utils/retry.py`) — transient error handling.
- **Event schema** documented in `docs/schema.md`.

**All tests passing locally:** 9 unit tests.

### 4. Events Query API ✅
- **`GET /api/events`** endpoint with:
  - `source` filter (git | ci | both).
  - `type` filter (event type matching).
  - `repo` filter (repository exact match).
  - `since` filter (ISO8601 timestamp).
  - `limit` parameter (default 50).
- **Unit tests** cover empty, populated, and filtered responses.
- **Fallback** to file-backed connectors if SQL store unavailable.

### 5. UX & Mockups ✅
- **Low-fidelity investigation canvas mockups** with:
  - Incident summary section (title, timing, severity, impact).
  - Timeline visualization (git, CI, monitoring events).
  - Annotations & notes (threaded, timestamped).
  - RCA conclusion (root cause, fix, status).
  - Export & Share buttons.

- **User flows** documented for conducting and sharing RCAs.

### 6. Security & Threat Model ✅
- **Baseline threat model** identifying Tier 1/2/3 threats:
  - Unauthorized access, injection attacks, data exposure.
  - MITM, DoS, privilege escalation.
  - Information disclosure.
- **Initial mitigations:** parameterized SQL, input validation.
- **Production recommendations:** auth/RBAC, encryption, audit logging, compliance.

### 7. Investigation Canvas Stories ✅
- **Story 1:** Investigation Canvas UI Prototype (5 pts).
- **Story 2:** Investigations Data Model & API (3 pts).
- **Story 3:** Event Linking & Annotations (5 pts).
- **Story 4:** Pilot Validation & Feedback (3 pts).

**Total story points:** 16 pts — estimated 2 sprints.

### 8. Documentation ✅
- `EPICS.md` — all 7 epics with acceptance criteria.
- `ROADMAP.md` — 6-month timeline.
- `BACKLOG.md` — prioritized backlog items.
- `docs/ARCHITECTURE.md` — core platform architecture.
- `docs/ux_mockups.md` — investigation canvas mockups and user flows.
- `docs/investigation_stories.md` — story breakdown.
- `docs/security_threat_model.md` — threat model and recommendations.
- `docs/api_events.md` — `/api/events` endpoint documentation.
- `docs/connectors_hardening.md` — validation and retry patterns.
- `docs/schema.md` — event schema (MVP).
- `CONTRIBUTING.md` — contribution guidelines.

## GitHub Issues Created

**Epics (closed or in progress):**
- #3: Core Platform & Architecture (closed)
- #4: Data & Integrations (closed)
- #5: RCA Workflow & UX (in progress — design phase)
- #9: Baseline Threat Model for MVP (closed)

**Stories (closed):**
- #6: Create repository skeleton and CI (closed)
- #7: Implement Git Event Connector (closed)
- #8: Design Investigation Canvas mockups (design phase)
- #11: Add Events Query API (closed)
- #12: Add SQL-backed event store and schema (closed)
- #14: Harden connectors — basic validation and retries (closed)
- #15: Extend Events API with filters (closed)

**Stories (ready for implementation):**
- #16: Investigation Canvas UI Prototype
- #17: Investigations Data Model & API
- #18: Event Linking & Annotations
- #19: Pilot Validation & Feedback

## Test Coverage

```
9 tests passing:
  ✓ test_index (app)
  ✓ test_api_events_empty
  ✓ test_api_events_with_data
  ✓ test_api_events_filters
  ✓ test_ingest_and_load (git connector)
  ✓ test_ci_ingest_and_load (ci connector)
  ✓ test_sql_insert_and_query (sql store)
  ✓ test_validator_accepts_valid
  ✓ test_validator_rejects_invalid
```

## How to Run

**Local Development:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.app
# Visit http://localhost:8080 and http://localhost:8080/api/events
```

**Tests:**

```bash
pytest -q
```

**Dev Sandbox (Docker):**

```bash
docker-compose -f infra/docker-compose.yml up --build
```

## Next Steps (Post-MVP)

1. **Implement investigation canvas UI** (Story #16).
2. **Build investigations data model and API** (Story #17).
3. **Add annotations and event linking** (Story #18).
4. **Pilot validation and iteration** (Story #19).
5. **Production hardening:** auth/RBAC, durable queues, compliance.
6. **Metrics and observability:** tracing, dashboards, alerts.

## Key Metrics

- **Repository stats:**
  - 15+ files (src, tests, docs, infra).
  - 9 unit tests (100% passing).
  - 7 epics, 15+ stories defined.
  
- **Timeline:** Completed in 1 session (~4-5 hours equivalent work).
- **Documentation:** 11+ markdown documents covering design, architecture, API, and user flows.

## Stakeholder Readiness

- ✅ PMO-aligned epics and roadmap.
- ✅ Clear MVP scope and phased delivery plan.
- ✅ Pilot-ready mockups and documentation.
- ✅ Security and compliance baseline.
- ✅ Developer onboarding guide (< 10 mins to get running).

---

**Project Status:** MVP Phase 1 Complete. Ready for Phase 2 (Investigation Canvas Implementation).
