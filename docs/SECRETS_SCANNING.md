# 🔐 Secrets Scanning Documentation

This document describes the comprehensive secrets scanning system for the Investigation RCA Platform.

## Overview

We use a multi-layered approach to prevent hardcoded secrets from being committed:

1. **Pre-commit Hooks** - Block secrets BEFORE they're committed locally
2. **GitHub Actions CI** - Final verification on PR/push
3. **Automated Scanning** - Multiple detection engines
4. **Custom Regex Patterns** - Project-specific secret patterns

---

## Pre-Commit Hooks

### Installation

```bash
# Install pre-commit framework
pip install pre-commit

# Install hooks from config
pre-commit install

# Test all files
pre-commit run --all-files

# Test staged files (what will run on commit)
pre-commit run
```

### What Gets Scanned

1. **TruffleHog** - Verified secrets (high confidence)
   - AWS credentials
   - API keys
   - Database credentials

2. **detect-secrets** - High-entropy strings
   - Random strings that look like secrets
   - Base64-encoded credentials

3. **git-secrets** - AWS-specific patterns
   - AWS access keys
   - AWS secret keys

4. **Custom Scripts**
   - API keys (.git-hooks/detect-api-keys.py)
   - Database URLs (.git-hooks/detect-db-urls.py)

### Supported Secret Types

| Secret Type | Pattern | Severity |
|------------|---------|----------|
| AWS Access Key | AKIA[0-9A-Z]{16} | CRITICAL |
| AWS Secret | aws_secret_access_key=... | CRITICAL |
| GitHub Token | gh[pousr]_[A-Za-z0-9_]{36,} | CRITICAL |
| Slack Token | xox[baprs]-... | CRITICAL |
| Stripe API Key | sk_(live\|test)_... | CRITICAL |
| JWT Token | eyJ...eyJ... | HIGH |
| Private Key | -----BEGIN PRIVATE KEY----- | CRITICAL |
| Database URL | postgres://user:pass@host/db | CRITICAL |
| API Key | api_key=... | HIGH |

### Running Manually

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run trufflehog --all-files
pre-commit run detect-secrets --all-files
pre-commit run detect-api-keys --all-files

# Run on specific file
pre-commit run --files path/to/file.py
```

### Bypassing (Emergency Only)

```bash
# Skip pre-commit checks (ONLY FOR EMERGENCIES)
git commit --no-verify

# This should be avoided and documented if used
```

### Configuration Files

- `.pre-commit-config.yaml` - Hook definitions and ordering
- `.git-hooks/detect-api-keys.py` - Custom API key patterns
- `.git-hooks/detect-db-urls.py` - Custom database URL patterns
- `.secrets.baseline` - Known/accepted secrets (reference only)

---

## GitHub Actions CI

### Secrets Scan Workflow

Location: `.github/workflows/secrets-scan.yml`

Runs on:
- Every push to `main` branch
- Every pull request to `main` branch

### Detection Methods

1. **detect-secrets** - High-entropy baseline scanning
2. **truffleHog** - Verified secrets with confidence scores
3. **git-secrets** - AWS pattern database
4. **Regex Patterns** - Custom secret patterns in Python

### Artifact Results

Failed scans upload artifacts:
- `.secrets.baseline` - Detection baseline
- `truffleHog-results.json` - Detailed findings

### Failing the Build

The CI will **FAIL** if:
- Verified secrets detected by TruffleHog
- AWS patterns matched by git-secrets
- Custom regex patterns matched (API keys, DB URLs)
- High-entropy strings in baseline

### View Results

```bash
# Check scan logs
gh run view <run_id> -l

# Download artifacts
gh run download <run_id> -n secrets-scan-results
```

---

## Best Practices

### ✅ DO:

1. **Use environment variables** for secrets
   ```python
   # Good
   api_key = os.getenv('STRIPE_API_KEY')
   ```

2. **Use `.env` files** (in `.gitignore`)
   ```
   # .env (NEVER COMMIT)
   STRIPE_API_KEY=sk_live_...
   DATABASE_URL=postgres://...
   ```

3. **Use example files** for documentation
   ```
   # .env.example (SAFE - can be committed)
   STRIPE_API_KEY=sk_test_example
   DATABASE_URL=postgres://user:pass@localhost/dbname
   ```

4. **Use GitHub Secrets** for CI/CD
   ```yaml
   - name: Deploy
     env:
       API_KEY: ${{ secrets.STRIPE_API_KEY }}
   ```

5. **Rotate exposed secrets immediately** if leaked

### ❌ DON'T:

1. **Never hardcode secrets** in code
   ```python
   # BAD - NEVER DO THIS
   api_key = "sk_live_4eC39HqLyjWDarht..."
   ```

2. **Never commit `.env`** files
   ```
   # .gitignore - MUST HAVE
   .env
   .env.local
   .env.*.local
   ```

3. **Never use test secrets** with real data
   ```python
   # BAD
   token = "real_production_token"
   ```

4. **Never skip the pre-commit hook**
   ```bash
   # BAD - Only for emergencies
   git commit --no-verify
   ```

---

## Troubleshooting

### Pre-commit hook fails but secret is safe

If you have a false positive (test data, example code), you can:

1. **Move to test file** (tests/ directory)
   ```python
   # tests/test_api.py - OK to have test data
   test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
   ```

2. **Mark as comment in code**
   ```python
   # This is example data for documentation
   example_key = "sk_test_example_key"
   ```

3. **Use .env.example** for documentation
   ```bash
   # .env.example - Can be committed
   STRIPE_API_KEY=sk_test_example
   ```

### Pre-commit hook won't install

```bash
# Remove old hooks
rm -rf .git/hooks/

# Reinstall
pre-commit install
pre-commit install --install-hooks

# Verify
pre-commit run --all-files
```

### CI scan timing out

- The full scan might take 1-2 minutes
- TruffleHog verified scans are slower
- Results are uploaded to artifacts

---

## Maintenance

### Weekly Tasks

1. Review baseline changes
   ```bash
   git diff .secrets.baseline
   ```

2. Check for new secret patterns to add

### Quarterly Tasks

1. Update detect-secrets
   ```bash
   pip install --upgrade detect-secrets
   ```

2. Update TruffleHog
   ```bash
   pip install --upgrade truffleHog
   ```

3. Audit allowed secrets in baseline

---

## Incident Response

If a secret is exposed:

### Immediate Actions (Within 1 hour)

1. **Revoke the credential** immediately
   - Generate new API keys
   - Reset passwords
   - Rotate tokens

2. **Remove from commit**
   ```bash
   # Use git-filter-branch or BFG Repo-Cleaner
   git filter-branch --tree-filter 'rm -f filename' HEAD
   ```

3. **Force push** (ONLY for exposed secrets)
   ```bash
   git push --force origin main
   ```

### Investigation

1. Check git history for exposure duration
2. Audit logs for unauthorized access
3. Notify affected systems/services
4. Document incident

### Prevention

1. Update scanning rules to catch this type
2. Add to monitoring/alerting
3. Review team practices
4. Update documentation

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  secrets-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run secrets scan
        run: |
          pip install detect-secrets truffleHog
          pre-commit run --all-files

  deploy:
    needs: secrets-check
    runs-on: ubuntu-latest
    # Deployment only happens after secrets scan passes
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        env:
          STRIPE_API_KEY: ${{ secrets.STRIPE_API_KEY }}
        run: ./scripts/deploy.sh
```

---

## Tools Reference

| Tool | Purpose | Speed | Confidence |
|------|---------|-------|-----------|
| detect-secrets | High-entropy patterns | Fast | Medium |
| TruffleHog | Verified secrets | Slow | High |
| git-secrets | AWS patterns | Fast | High |
| Custom regex | Project-specific | Very Fast | Medium |

---

## Questions?

For secrets scanning questions or issues, refer to:
- `.github/workflows/secrets-scan.yml` - CI configuration
- `.pre-commit-config.yaml` - Local hook configuration
- `.git-hooks/detect-api-keys.py` - API key detection logic
- `.git-hooks/detect-db-urls.py` - Database URL detection logic

---

**Last Updated**: 2026-01-28
**Status**: ✅ Production Ready
