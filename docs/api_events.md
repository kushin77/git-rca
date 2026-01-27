# Events Query API

Endpoint: `/api/events`

Query parameters:
- `source` (optional): `git` or `ci`. If omitted, both sources are returned.
- `limit` (optional): maximum number of events to return (default `50`).

Filtering parameters:
- `type` (optional): filter by event `type` (e.g., `push`, `pull_request`).
- `repo` (optional): filter events by `repo` field (exact match).
- `since` (optional): ISO8601 timestamp string; only events with `timestamp` or internal `_inserted_at` >= `since` are returned.

Response:

```json
{
  "count": 2,
  "events": [ ... ]
}
```

This endpoint aggregates events from development connectors (`git_connector`, `ci_connector`). It's intended for dev/testing; production implementations should add pagination, timestamps, sorting, authentication, and authorization.
