```markdown
# Security Threat Model & Immediate Hardening Checklist

Status: Baseline threat model for MVP. This document consolidates the MVP findings and lists P0 actions required before any production deployment.

Top-tier threats (Tier 1)
- Unauthorized access to API or stored RCAs (data exposure)
- Secrets leaked in repo or CI variables
- Injection (SQL / command) leading to data corruption or RCE

Mid-tier threats (Tier 2)
- Denial-of-service on public endpoints
- Privilege escalation via misconfigured dependencies
- Inadequate audit logging and tamperable records

Low-tier threats (Tier 3)
- Information disclosure in error messages
- Weak transport encryption in integrations

Immediate P0 hardening checklist (do these now)
1. Secrets & credentials
   - Run a secrets scan (truffleHog, git-secrets) across history; rotate any leaked tokens immediately.
   - Add a CI job to fail PRs with regex-detected secrets.
2. Auth & RBAC
   - Add token-based auth to all non-public endpoints. Default to deny-all.
   - Define minimal roles (admin, engineer, viewer) and enforce RBAC on write actions.
3. Input validation & parameterization
   - Use parameterized SQL queries everywhere (no string concatenation). Audit `src/store/sql_store.py`.
   - Apply JSON Schema validation to all ingested events (use `jsonschema`).
4. CI/CD safety
   - Remove hard-coded tokens from scripts (e.g., `GITHUB_CLOSURE_AUTOMATION.sh`) and require use of `secrets` or env vars injected by CI.
   - Gate merges on passing security checks and tests.

Production hardening (Phase 2)
- Use durable queuing (Pub/Sub/Kafka) for incoming events and idempotent processing.
- Enable TLS for internal communications and enforce HTTPS with HSTS.
- Add structured audit logging with immutable retention (append-only logs, WORM where required).
- Run SCA (Dependabot/Snyk) and container scanning on image builds.
- Implement rate-limiting and circuit-breakers for external integrations.

Detection & monitoring
- Add metrics: event ingestion rate, dropped events, DB error rate, auth failure rate.
- Hook traces for incoming requests (OpenTelemetry) and set error-rate alerts.
- Create security incident playbook and runbook for token compromise.

Checklist for code reviewers
- Are all DB queries parameterized? (yes/no)
- Are inputs validated against a schema? (yes/no)
- Any secrets in code or CI configs? (none/flagged)
- Is authentication required for write endpoints? (yes/no)

Tools & references
- `trufflehog`, `git-secrets` — history scanning
- `jsonschema`, `marshmallow` — input validation
- `tenacity` — robust retry/backoff
- OpenTelemetry / Prometheus / Grafana — observability

Owner: Security, Compliance & Privacy epic

Next actions I will take (with your approval)
1. Run a local secrets scan and produce a findings report.
2. Create P0 issues for secret rotation, auth middleware, and CI gate hardening (I already drafted canonical issues manifest).

``` 
