"""
Git Connector - Monitor Git repository events and commits

Features:
- Fetch recent commits from repository
- Detect merge conflicts and large commits
- Monitor branch changes and tags
- Extract commit metadata (author, files changed, etc.)
"""

import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from src.models.event import Event, EventSource, EventSeverity
from src.connectors.base_connector import BaseConnector, RetryPolicy, CircuitBreakerConfig


class GitConnector(BaseConnector):
    """Monitor Git repository for events and commits."""

    def __init__(self,
                 repo_path: str = ".",
                 lookback_commits: int = 10,
                 retry_policy: RetryPolicy = None,
                 circuit_breaker_config: CircuitBreakerConfig = None):
        """
        Initialize Git connector.

        Args:
            repo_path: Path to Git repository
            lookback_commits: Number of recent commits to check
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            source=EventSource.GIT,
            retry_policy=retry_policy,
            circuit_breaker_config=circuit_breaker_config,
        )
        self.repo_path = Path(repo_path).resolve()
        self.lookback_commits = lookback_commits

    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect recent Git commits and repository events.

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Get recent commits
            commits = self._get_recent_commits()
            for commit in commits:
                event = self._create_commit_event(commit)
                if event:
                    events.append(event)

            # Check for potential issues
            issues = self._check_repo_issues()
            events.extend(issues)

        except Exception as e:
            self.logger.error(f"Failed to collect Git events: {e}")
            raise  # Re-raise for retry logic

        return events

    def _get_recent_commits(self) -> List[Dict[str, Any]]:
        """Get recent commits from repository."""
        try:
            # Get commit info with --pretty=format and --stat
            cmd = [
                "git", "log",
                f"-{self.lookback_commits}",
                "--pretty=format:COMMIT_START%nHash: %H%nAuthor: %an <%ae>%nDate: %ai%nSubject: %s%nBody: %b%nFiles: %N%nInsertions: %w(0,0,0)",
                "--stat=1000",  # Limit stat width
                "--no-merges"   # Skip merge commits for cleaner output
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.logger.warning(f"Git log failed: {result.stderr}")
                return []

            return self._parse_git_log(result.stdout)

        except subprocess.TimeoutExpired:
            self.logger.warning("Git log command timed out")
            return []
        except FileNotFoundError:
            self.logger.warning("Git command not found")
            return []

    def _parse_git_log(self, output: str) -> List[Dict[str, Any]]:
        """Parse git log output into commit dictionaries."""
        commits = []
        sections = output.split("COMMIT_START\n")

        for section in sections[1:]:  # Skip empty first section
            lines = section.strip().split('\n')
            if len(lines) < 5:
                continue

            commit = {}

            # Parse header
            for line in lines:
                if line.startswith("Hash: "):
                    commit["hash"] = line[6:]
                elif line.startswith("Author: "):
                    commit["author"] = line[8:]
                elif line.startswith("Date: "):
                    commit["date"] = line[6:]
                elif line.startswith("Subject: "):
                    commit["subject"] = line[9:]
                elif line.startswith("Body: "):
                    commit["body"] = line[6:]
                elif line.startswith("Files: "):
                    commit["files_changed"] = int(line[7:]) if line[7:].isdigit() else 0
                elif line.startswith("Insertions: "):
                    commit["insertions"] = int(line[12:]) if line[12:].isdigit() else 0

            if commit.get("hash"):
                commits.append(commit)

        return commits

    def _create_commit_event(self, commit: Dict[str, Any]) -> Optional[Event]:
        """Create an Event from commit data."""
        try:
            # Determine severity based on commit characteristics
            severity = EventSeverity.INFO

            # Large commits might indicate issues
            if commit.get("files_changed", 0) > 50:
                severity = EventSeverity.WARNING
            if commit.get("insertions", 0) > 10000:  # 10k+ lines
                severity = EventSeverity.CRITICAL

            # Check for concerning keywords in subject/body
            concerning_keywords = ["fix", "bug", "error", "fail", "break"]
            text = (commit.get("subject", "") + " " + commit.get("body", "")).lower()
            if any(keyword in text for keyword in concerning_keywords):
                severity = max(severity, EventSeverity.WARNING)

            return Event(
                timestamp=commit["date"],
                source=EventSource.GIT,
                event_type='commit',
                severity=severity,
                data={
                    "commit_hash": commit["hash"],
                    "author": commit["author"],
                    "subject": commit["subject"],
                    "body": commit.get("body", ""),
                    "files_changed": commit.get("files_changed", 0),
                    "insertions": commit.get("insertions", 0),
                },
                source_id=commit["hash"],
                tags=["commit", commit["author"].split('<')[0].strip()],
                metadata={
                    "commit_hash": commit["hash"],
                    "author": commit["author"],
                    "subject": commit["subject"],
                    "body": commit.get("body", ""),
                    "files_changed": commit.get("files_changed", 0),
                    "insertions": commit.get("insertions", 0),
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to create commit event: {e}")
            return None

    def _check_repo_issues(self) -> List[Event]:
        """Check for repository issues like uncommitted changes, conflicts, etc."""
        events = []

        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                events.append(Event(
                    timestamp=datetime.utcnow().isoformat(),
                    source=EventSource.GIT,
                    event_type='uncommitted_changes',
                    severity=EventSeverity.WARNING,
                    data={
                        "changes": lines,
                        "change_count": len(lines),
                    },
                    source_id=f"uncommitted-{datetime.utcnow().isoformat()}",
                    tags=["uncommitted", "changes"],
                    metadata={"changes": lines}
                ))

            # Check for merge conflicts
            result = subprocess.run(
                ["git", "ls-files", "--unmerged"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                events.append(Event(
                    timestamp=datetime.utcnow().isoformat(),
                    source=EventSource.GIT,
                    event_type='merge_conflict',
                    severity=EventSeverity.CRITICAL,
                    data={
                        "conflicted_files": lines,
                        "conflict_count": len(lines),
                    },
                    source_id=f"conflicts-{datetime.utcnow().isoformat()}",
                    tags=["conflict", "merge"],
                    metadata={"conflicted_files": lines}
                ))

        except Exception as e:
            self.logger.error(f"Failed to check repo issues: {e}")

        return events
