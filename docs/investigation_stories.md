# Investigation Canvas User Stories

This file breaks down the investigation canvas implementation into user stories for the MVP.

## Story 1: Investigation Canvas UI Prototype

**Epic:** RCA Workflow & UX

**Description:**
Create an interactive HTML/CSS prototype of the investigation canvas with collapsible sections for incident summary, timeline, annotations, and RCA conclusion. Mock data is served from `/api/events` for the timeline.

**Acceptance Criteria:**
- Static HTML mockup renders in browser (responsive, mobile-friendly).
- Incident summary, timeline, annotations, and RCA sections are collapsible.
- Timeline is populated with mock git/ci events in chronological order.
- [Save], [Export PDF], and [Share] buttons are present (non-functional for MVP).

**Story Points:** 5

---

## Story 2: Investigations Data Model & API

**Epic:** Data & Integrations

**Description:**
Add a simple investigations table to SQLite (or new schema) with fields: id, title, start_time, duration, severity, impact, root_cause, fix, status, created_by, created_at, updated_at. Add a REST endpoint `POST /api/investigations` to create and update investigations.

**Acceptance Criteria:**
- SQLite schema migration or init script creates `investigations` table.
- `POST /api/investigations` creates a new investigation with incident summary and RCA fields.
- `GET /api/investigations/<id>` retrieves an investigation.
- Unit tests cover create and retrieve paths.

**Story Points:** 3

---

## Story 3: Event Linking & Annotations

**Epic:** RCA Workflow & UX

**Description:**
Add annotation support to the canvas: engineers can add notes tied to specific events (with timestamps and author info) and link events together to show causal relationships.

**Acceptance Criteria:**
- Annotation UI allows text input tied to a specific timeline event.
- Annotations are persisted to a new `annotations` table.
- UI shows annotations threaded under their associated event.
- A simple link/relation UI lets engineers mark events as related.

**Story Points:** 5

---

## Story 4: Pilot Validation & Feedback

**Epic:** Adoption, Docs & Enablement

**Description:**
Onboard a pilot team with the investigation canvas prototype. Collect feedback, validate UX, and iterate on the mockups.

**Acceptance Criteria:**
- Pilot feedback documented in `docs/pilot_feedback.md`.
- Two pilot engineers have used the canvas end-to-end.
- Issues and improvement suggestions are logged.

**Story Points:** 3

---

## Prioritization (MoSCoW)

- **Must-have (M):** Story 1 (prototype UI).
- **Should-have (S):** Story 2 (API) and Story 3 (annotations).
- **Could-have (C):** Story 4 (pilot validation) — run after M/S items are done.
