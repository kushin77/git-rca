#!/usr/bin/env python3
"""Prevent .venv and .env.local from being committed."""

import subprocess
import sys
import re

try:
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        capture_output=True,
        text=True,
        check=True,
    )
    files = result.stdout.strip().split('\n')
except Exception:
    sys.exit(0)

forbidden_patterns = [r'\.venv/', r'\.env\.local']
found = False

for f in files:
    if f and any(re.search(pattern, f) for pattern in forbidden_patterns):
        print(f'❌ ERROR: {f} should not be committed')
        found = True

if found:
    print('\n❌ .venv and .env.local files cannot be committed')
    sys.exit(1)

sys.exit(0)
