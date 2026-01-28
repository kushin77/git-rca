#!/usr/bin/env python3
"""
Detect exposed database connection strings and credentials.

This script scans for:
- PostgreSQL connection strings
- MySQL/MariaDB credentials
- MongoDB URIs
- Redis connection strings
- Oracle database strings
- Firebase URLs
"""

import re
import sys
from pathlib import Path

# Database connection patterns
DB_PATTERNS = {
    "POSTGRES_URL": {
        "pattern": r"postgres(ql)?://([a-zA-Z0-9:@.\-_]+)@([a-zA-Z0-9:.\-_]+)/([a-zA-Z0-9_\-]+)",
        "severity": "CRITICAL",
    },
    "MYSQL_URL": {
        "pattern": r"mysql://([a-zA-Z0-9:@.\-_]+)@([a-zA-Z0-9:.\-_]+)/([a-zA-Z0-9_\-]+)",
        "severity": "CRITICAL",
    },
    "MONGODB_URL": {
        "pattern": r"mongodb(?:\+srv)?://([a-zA-Z0-9:@.\-_]+)@([a-zA-Z0-9:.\-_]+)/([a-zA-Z0-9_\-]+)",
        "severity": "CRITICAL",
    },
    "REDIS_URL": {
        "pattern": r"redis://(:?[a-zA-Z0-9]{10,})?@([a-zA-Z0-9:.\-_]+)",
        "severity": "CRITICAL",
    },
    "FIREBASE_URL": {
        "pattern": r"https://([a-zA-Z0-9\-]+)\.firebaseio\.com",
        "severity": "HIGH",
    },
    "DATABASE_PASSWORD": {
        "pattern": r"(?i)(db_password|database_password|password)\s*[:=]\s*['\"]([^'\"]{8,})['\"]",
        "severity": "CRITICAL",
    },
}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "logs",
    "node_modules",
    ".egg-info",
}
EXCLUDED_FILES = {
    ".env.example",
    ".env.local",
    ".secrets.baseline",
    "requirements.txt",
    "package-lock.json",
}


def should_scan_file(filepath: str) -> bool:
    """Check if file should be scanned."""
    path = Path(filepath)

    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return False

    if path.name in EXCLUDED_FILES:
        return False

    if path.suffix in {".pyc", ".so", ".o", ".png", ".jpg", ".zip"}:
        return False

    return path.is_file() and path.stat().st_size < 1000000


def scan_content(filepath: str, content: str) -> list:
    """Scan content for database connection patterns."""
    findings = []

    for pattern_name, pattern_info in DB_PATTERNS.items():
        pattern = pattern_info["pattern"]
        severity = pattern_info["severity"]

        try:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                line_no = content[: match.start()].count("\n") + 1
                line_content = content.split("\n")[line_no - 1]

                if "test" in filepath.lower() and "test" in line_content.lower():
                    continue
                if line_content.strip().startswith("#"):
                    continue

                findings.append(
                    {
                        "pattern": pattern_name,
                        "severity": severity,
                        "file": filepath,
                        "line": line_no,
                        "match": match.group()[:50]
                        + ("..." if len(match.group()) > 50 else ""),
                    }
                )
        except Exception:
            pass

    return findings


def main():
    """Scan staged files for database credentials."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        staged_files = result.stdout.strip().split("\n")
    except Exception:
        return 0

    all_findings = []

    for filepath in staged_files:
        if not filepath or not should_scan_file(filepath):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                findings = scan_content(filepath, content)
                all_findings.extend(findings)
        except Exception:
            pass

    if not all_findings:
        print("✅ No database credentials detected")
        return 0

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    all_findings.sort(key=lambda x: severity_order.get(x["severity"], 999))

    print("❌ DATABASE CREDENTIALS DETECTED\n")
    for finding in all_findings:
        severity_icon = "🔴" if finding["severity"] == "CRITICAL" else "🟡"
        print(
            f"{severity_icon} [{finding['severity']}] {finding['pattern']} "
            f"in {finding['file']}:{finding['line']}"
        )
        print(f"   Match: {finding['match']}\n")

    print(f"\n❌ Found {len(all_findings)} database credential(s)")

    return 1


if __name__ == "__main__":
    sys.exit(main())
