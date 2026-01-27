# Architecture Overview

This document provides a concise architecture overview for the Git RCA Workspace MVP.

Core concepts:

- Monorepo layout: `src/` contains services and connectors; `tests/` contains unit tests; `docs/` holds documentation.
- Connectors: lightweight adapters that ingest external signals (e.g., git events, CI/monitoring events) into the data layer.
- API: a minimal Flask service (`src/app.py`) exposing developer-friendly endpoints, e.g., `/api/events` for dev queries.
- Dev sandbox: `Dockerfile` + `infra/docker-compose.yml` provide a reproducible local environment.
- CI: GitHub Actions pipeline runs tests on push/PR (.github/workflows/ci.yml).

Data flow (dev):

1. External systems -> connectors (ingest events) -> local JSONL dev stores under `data/`.
2. `/api/events` aggregates connector stores and returns recent events for quick queries and UI prototyping.

Security and production notes:

- The current dev connectors are file-backed and intentionally minimal. Production connectors must implement durable storage, authentication, batching, retry, and schema validation.
- The API should add authentication, RBAC, pagination, and stricter validation before any external exposure.
- IaC and environment provisioning (Terraform/CloudFormation/ARM) should be added for real sandbox and production deployments.

Next steps:

- Add an event schema and a small query service backed by a lightweight DB (e.g., SQLite/Postgres) for the dev environment.
- Add IaC for provisioning a dev sandbox in cloud (optional) and a more complete architecture diagram in `docs/diagrams/`.
