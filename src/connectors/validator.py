from typing import Dict

REQUIRED_FIELDS = ["type"]


def validate_event(event: Dict) -> bool:
    """Basic validation for events. Returns True if valid, False otherwise.

    This validator is intentionally permissive for dev: accept events that have
    a `type` field or other common indicators like `status`, `job`, `repo`,
    `commit`, or `id`.
    """
    if not isinstance(event, dict):
        return False
    if "type" in event:
        return True
    # accept CI-style events lacking explicit `type`
    for k in ("status", "job", "repo", "commit", "id"):
        if k in event:
            return True
    return False
