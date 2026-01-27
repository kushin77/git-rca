# Organizational Memory Engine — Discovery & Initial Plan

This document outlines a pragmatic, phased plan to implement an Organizational Memory Engine (OME) for the org. It is intended as a starting point to capture scope, deliverables, and a minimal PoC backlog.

Goals
- Collect and index key organizational artifacts (issues, PRs, ADRs, docs).
- Produce per-repo contextual summaries suitable for Copilot context files.
- Provide search and retrieval endpoints for teams to query org knowledge.

Phases
- Phase 1 (PoC, 2-4 weeks):
  - Collector for GitHub issues and PRs (3 repos)
  - Simple classifier (issue/decision/incident)
  - Generate per-repo context files in `.copilot/`
  - Deliverable: `docs/OME_POC.md` and demo

- Phase 2 (Automation, 4-8 weeks):
  - Expand collectors (PR reviews, ADRs, wiki)
  - Add scheduled ingestion pipeline and embeddings for semantic search
  - Basic UI for search and timeline

- Phase 3 (Scale, ongoing):
  - Add more sources (Slack, PagerDuty), relationship graph, role-based contexts
  - Integrate with Copilot context distribution and workspace sync

Next steps
1. Create Issue #2 comment linking this doc and ask for prioritization.
2. Implement Phase 1 collector prototype on branch `feature/ome-poc`.

Notes
- This is an initial plan — scope and timelines should be adjusted after stakeholder alignment.
