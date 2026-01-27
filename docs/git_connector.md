# Git Event Connector (DEV)

This connector is a lightweight, file-backed implementation for development and testing. It allows ingesting git-related events (push, pull request, branch events) into a local JSONL store for exploration.

Usage

```py
from src.connectors.git_connector import ingest_event, load_events, clear_store

clear_store()
ingest_event({"type": "push", "repo": "example/repo", "commit": "abc123"})
events = load_events()
```

Notes

- This implementation is intentionally minimal for the MVP/dev loop. Production connectors should implement durable storage, authentication, retries, batching, and schema validation.
- The file lives under `data/dev_git_events.jsonl` by default.
