#!/usr/bin/env python3
"""
Detect exposed API keys, tokens, and credentials in code.

This script scans for common patterns of exposed secrets:
- AWS access keys
- API keys for popular services (Stripe, Slack, GitHub, etc.)
- JWT tokens
- Database connection strings
- Private keys and certificates
"""

import re
import sys
from pathlib import Path

# Patterns for common secrets
PATTERNS = {
    "AWS_ACCESS_KEY": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "severity": "CRITICAL",
    },
    "AWS_SECRET_KEY": {
        "pattern": r'(?i)aws_secret_access_key\s*[:=]\s*[\'"]?[A-Za-z0-9/+=]{40}[\'"]?',
        "severity": "CRITICAL",
    },
    "GITHUB_TOKEN": {
        "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,255}",
        "severity": "CRITICAL",
    },
    "GITHUB_PAT": {
        "pattern": r'github[_-]?token[_=:\s]*[\'"]?[A-Za-z0-9_]{40,}[\'"]?',
        "severity": "CRITICAL",
    },
    "SLACK_TOKEN": {
        "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9_-]{32}",
        "severity": "CRITICAL",
    },
    "STRIPE_API_KEY": {
        "pattern": r"sk_(live|test)_[0-9a-zA-Z]{20,}",
        "severity": "CRITICAL",
    },
    "STRIPE_RESTRICTED_KEY": {
        "pattern": r"rk_(live|test)_[0-9a-zA-Z]{20,}",
        "severity": "CRITICAL",
    },
    "JWT_TOKEN": {
        "pattern": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "severity": "HIGH",
    },
    "GENERIC_API_KEY": {
        "pattern": r'(?i)(api[_-]?key|apikey|access[_-]?token)\s*[:=]\s*[\'"]?([A-Za-z0-9\-_]{20,})[\'"]?',
        "severity": "HIGH",
    },
    "DATABASE_URL": {
        "pattern": r"(postgres|mysql|mongodb|redis)://[a-zA-Z0-9:@/.?#\[\]@!$&\'()*+,;=%_-]{20,}",
        "severity": "HIGH",
    },
    "PRIVATE_KEY": {
        "pattern": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
        "severity": "CRITICAL",
    },
    "CERTIFICATE": {
        "pattern": r"-----BEGIN CERTIFICATE-----",
        "severity": "HIGH",
    },
    "JWT_SECRET": {
        "pattern": r'(?i)(jwt[_-]?secret|jwt[_-]?key)\s*[:=]\s*[\'"]?([A-Za-z0-9\-_]{20,})[\'"]?',
        "severity": "CRITICAL",
    },
    "SENDGRID_KEY": {
        "pattern": r"SG\.[a-zA-Z0-9_-]{66}",
        "severity": "CRITICAL",
    },
    "MAILCHIMP_KEY": {
        "pattern": r"[a-f0-9]{32}-us[0-9]{1,2}",
        "severity": "HIGH",
    },
}

# Files to skip
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
    "poetry.lock",
}
EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".so",
    ".o",
    ".a",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".zip",
    ".tar",
    ".gz",
}


def should_scan_file(filepath: str) -> bool:
    """Check if file should be scanned."""
    path = Path(filepath)

    # Check excluded directories
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return False

    # Check excluded files
    if path.name in EXCLUDED_FILES:
        return False

    # Check excluded extensions
    if path.suffix in EXCLUDED_EXTENSIONS:
        return False

    # Skip very large files
    if path.is_file() and path.stat().st_size > 1000000:  # 1MB
        return False

    return True


def scan_content(filepath: str, content: str) -> list:
    """Scan content for secret patterns."""
    findings = []

    for pattern_name, pattern_info in PATTERNS.items():
        pattern = pattern_info["pattern"]
        severity = pattern_info["severity"]

        try:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                # Skip if in comment or test code
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
    """Scan staged files for secrets."""
    import subprocess

    # Get staged files
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
        print("✅ No secrets detected")
        return 0

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_findings.sort(key=lambda x: severity_order.get(x["severity"], 999))

    print("❌ SECRETS DETECTED\n")
    for finding in all_findings:
        severity_icon = "🔴" if finding["severity"] == "CRITICAL" else "🟡"
        print(
            f"{severity_icon} [{finding['severity']}] {finding['pattern']} "
            f"in {finding['file']}:{finding['line']}"
        )
        print(f"   Match: {finding['match']}\n")

    print(f"\n❌ Found {len(all_findings)} secret(s)")
    print("   To commit anyway: git commit --no-verify (EMERGENCY ONLY)")

    return 1


if __name__ == "__main__":
    sys.exit(main())
