# UX Mockups: Investigation Canvas (Low-Fidelity)

This document provides ASCII mockups and descriptions for the MVP RCA investigation canvas.

## Investigation Canvas Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Git RCA Workspace - Investigation [ID: RCA-2026-001]                    │
├─────────────────────────────────────────────────────────────────────────┤
│ [← Back]  [Save]  [Export PDF]  [Share]                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│ INCIDENT SUMMARY (collapsible)                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ Title:          [Service API outage]                             │    │
│ │ Start Time:     [2026-01-27 10:15:00 UTC]                       │    │
│ │ Duration:       [45 minutes]                                     │    │
│ │ Severity:       [Critical]                                       │    │
│ │ Impact:         [5k requests/sec failed]                         │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│ TIMELINE (main content area)                                            │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ 2026-01-27 10:00:00 │ [GIT] commit abc123 deployed to prod      │    │
│ │                     │   repo: api/core, branch: main            │    │
│ │                     │ [ANNOTATE] [LINK]                         │    │
│ │                     │                                            │    │
│ │ 2026-01-27 10:15:00 │ [CI] build job #5432 FAILED              │    │
│ │                     │   build time: 4s, error: assertion        │    │
│ │                     │ [ANNOTATE] [LINK]                         │    │
│ │                     │                                            │    │
│ │ 2026-01-27 10:16:00 │ [MONITORING] latency spike detected       │    │
│ │                     │   p99: 2.5s, normal: 50ms                │    │
│ │                     │ [ANNOTATE] [LINK]                         │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│ NOTES & ANNOTATIONS (collapsible)                                       │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ Engineer notes:                                                  │    │
│ │ ┌────────────────────────────────────────────────────────────┐   │    │
│ │ │ [2026-01-27 10:15 by alice@example.com]                   │   │    │
│ │ │ "Build failure on commit abc123 caused by missing env var" │   │    │
│ │ └────────────────────────────────────────────────────────────┘   │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│ ROOT CAUSE ANALYSIS (conclusion)                                        │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ Root Cause:  env var DB_HOST not set in deployment config      │    │
│ │ Fix:         Updated config and redeployed                      │    │
│ │ Status:      RESOLVED                                            │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Features

1. **Incident Summary** — quick contextual info (title, timing, severity, impact).
2. **Timeline** — chronological list of events (git, ci, monitoring) with sources and details.
   - Each event is collapsible and has quick-action buttons: [ANNOTATE] to add notes, [LINK] to relate events.
3. **Annotations** — threaded notes tied to specific events, searchable and timestamped.
4. **RCA Section** — captures the root cause, fixes applied, and resolution status.
5. **Export & Share** — buttons for PDF export and sharing the investigation with the team.

## User Flows

### Scenario 1: Engineer Conducting an RCA

1. Engineer clicks "New Investigation" and enters incident summary.
2. System queries `/api/events?since=<incident_start>&type=*&repo=*` to fetch related events.
3. Timeline is auto-populated and sorted chronologically.
4. Engineer adds annotations to events, links events together, and documents findings.
5. Engineer fills in the RCA conclusion and clicks "Save" and "Export PDF".

### Scenario 2: Sharing Investigation with Team

1. Engineer clicks "Share" and generates a read-only link.
2. Team members can view the investigation without editing; comments are read-only.

## Next Steps (Implementation)

1. **HTML/CSS Prototype** — create a simple, responsive HTML mockup with inline CSS.
2. **JS Event Binding** — wire the mockup to the Flask app and `/api/events` API.
3. **Data Binding** — sync the canvas form data (incident summary, annotations, RCA) to a new endpoint (e.g., `POST /api/investigations`).
