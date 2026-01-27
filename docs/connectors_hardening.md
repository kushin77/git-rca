# Connectors Hardening (Dev / Staging)

This page documents the lightweight hardening added to connectors in the MVP and recommended next steps for production.

What was added (MVP dev):
- Basic event validation: `src/connectors/validator.py` — accepts events with `type` or common keys (`status`, `job`, `repo`, `commit`, `id`).
- Simple retry decorator: `src/utils/retry.py` — used by `src/store/sql_store.insert_event` to retry transient DB errors.
- Connectors (`git_connector`, `ci_connector`) validate events and write to the SQL store with retries.

Why:
- Reduce data loss during transient DB errors.
- Provide basic input validation to avoid storing malformed payloads.

Production recommendations:
- Use JSON Schema validation (e.g., `jsonschema`) with strict rules and explicit types.
- Use robust retries with exponential backoff and jitter (e.g., `tenacity`).
- Persist events to durable queues/streams (Kafka, Pub/Sub) before processing.
- Add observability: metrics for dropped events, insert failures, and retry counts.
