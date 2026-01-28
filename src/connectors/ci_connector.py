"""
CI Connector - Monitor CI/CD pipeline events and job statuses

Features:
- Fetch CI pipeline/job status from CI systems
- Detect failed builds and deployments
- Monitor build times and success rates
- Extract job metadata (duration, artifacts, etc.)
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from src.models.event import Event, EventSource, EventSeverity
from src.connectors.base_connector import BaseConnector, RetryPolicy, CircuitBreakerConfig


class CIConnector(BaseConnector):
    """Monitor CI/CD pipelines for events and job statuses."""

    # CI status patterns to detect
    FAILURE_PATTERNS = [
        "failed", "failure", "error", "errored", "broken",
        "cancelled", "aborted", "timeout", "timed_out"
    ]

    SUCCESS_PATTERNS = [
        "success", "passed", "completed", "succeeded"
    ]

    def __init__(self,
                 ci_source: str = "github_actions",  # github_actions, jenkins, gitlab_ci, etc.
                 repo_owner: str = None,
                 repo_name: str = None,
                 lookback_hours: int = 24,
                 retry_policy: RetryPolicy = None,
                 circuit_breaker_config: CircuitBreakerConfig = None):
        """
        Initialize CI connector.

        Args:
            ci_source: CI system (github_actions, jenkins, gitlab_ci)
            repo_owner: Repository owner for filtering
            repo_name: Repository name for filtering
            lookback_hours: Hours to look back for CI events
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            source=EventSource.CI,
            retry_policy=retry_policy,
            circuit_breaker_config=circuit_breaker_config,
        )
        self.ci_source = ci_source
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.lookback_hours = lookback_hours

    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect CI pipeline and job events.

        Returns:
            List of Event objects
        """
        events = []

        try:
            # In development, simulate CI events or read from file
            # In production, this would query actual CI APIs
            ci_events = self._get_ci_events()
            for event_data in ci_events:
                event = self._create_ci_event(event_data)
                if event:
                    events.append(event)

        except Exception as e:
            self.logger.error(f"Failed to collect CI events: {e}")
            raise  # Re-raise for retry logic

        return events

    def _get_ci_events(self) -> List[Dict[str, Any]]:
        """Get CI events from source or simulate for development."""
        # For development, simulate some CI events
        # In production, this would query GitHub Actions API, Jenkins API, etc.

        events = []
        now = datetime.utcnow()

        # Simulate recent CI runs
        for i in range(random.randint(1, 5)):
            run_time = now - timedelta(hours=random.randint(0, self.lookback_hours))

            # Randomly generate CI run data
            statuses = ["success", "failure", "cancelled", "in_progress"]
            weights = [0.7, 0.2, 0.05, 0.05]  # Most runs succeed

            status = random.choices(statuses, weights=weights)[0]

            event = {
                "id": f"ci-run-{i+1}",
                "status": status,
                "workflow": f"CI Pipeline {i+1}",
                "branch": "main" if random.random() > 0.3 else f"feature-{i}",
                "commit": f"abc123{i}",
                "run_time": run_time.isoformat(),
                "duration_seconds": random.randint(60, 3600),  # 1min to 1hr
                "jobs": random.randint(1, 10),
                "artifacts": random.randint(0, 5),
            }
            events.append(event)

        return events

    def _create_ci_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """Create an Event from CI event data."""
        try:
            # Determine severity based on CI status
            status = event_data.get("status", "").lower()
            severity = EventSeverity.INFO

            if any(pattern in status for pattern in self.FAILURE_PATTERNS):
                severity = EventSeverity.CRITICAL
            elif status == "in_progress":
                severity = EventSeverity.WARNING
            elif any(pattern in status for pattern in self.SUCCESS_PATTERNS):
                severity = EventSeverity.INFO

            # Check for long-running builds
            duration = event_data.get("duration_seconds", 0)
            if duration > 3600:  # Over 1 hour
                severity = max(severity, EventSeverity.WARNING)

            title = f"CI {event_data['workflow']}: {status.title()}"
            description = f"Branch: {event_data['branch']} | Duration: {duration}s | Jobs: {event_data['jobs']}"

            return Event(
                timestamp=event_data["run_time"],
                source=EventSource.CI,
                event_type='ci_run',
                severity=severity,
                data={
                    "workflow": event_data["workflow"],
                    "status": event_data["status"],
                    "branch": event_data["branch"],
                    "commit": event_data["commit"],
                    "duration_seconds": duration,
                    "jobs_count": event_data["jobs"],
                    "artifacts_count": event_data["artifacts"],
                },
                source_id=event_data["id"],
                tags=["ci", event_data["status"], event_data["workflow"]],
                metadata={
                    "workflow": event_data["workflow"],
                    "status": event_data["status"],
                    "branch": event_data["branch"],
                    "commit": event_data["commit"],
                    "duration_seconds": duration,
                    "jobs_count": event_data["jobs"],
                    "artifacts_count": event_data["artifacts"],
                    "ci_source": self.ci_source,
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to create CI event: {e}")
            return None
