# CI / Monitoring Connector (DEV)

This connector provides a lightweight, file-backed implementation for ingesting CI/monitoring events into a local JSONL store for development and testing.

Usage

```py
from src.connectors.ci_connector import ingest_event, load_events, clear_store

clear_store()
ingest_event({"status": "passed", "job": "build", "id": "job-1"})
events = load_events()
```

Notes

- Intended for development only. Production connectors should use durable storage, authentication, batching, retries, and schema validation.
- Store location: `data/dev_ci_events.jsonl` by default.
