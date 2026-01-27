# Event Schema (MVP)

This document defines a minimal event schema for the MVP to support root-cause workflows and queries.

Core fields (common):
- `type` (string): event type (e.g., `push`, `pull_request`, `ci_job`).
- `source` (string): originating system (`git`, `ci`, `monitoring`).
- `repo` (string, optional): repository identifier for code-related events.
- `commit` (string, optional): commit SHA where applicable.
- `id` (string|int, optional): event id from source.
- `timestamp` (string, optional): ISO8601 timestamp from the source.
- `payload` (object, optional): source-specific details.

Notes:
- In the SQLite store we keep the entire event as JSON in `payload` and index by `source`. For production, use a structured table with typed columns and indexes for search.
