# FAANG-Grade Code & Architecture Audit

Date: 2026-01-28  
Status: MVP Phase 1 Complete; P0 Issues Identified

## Executive Summary

**Overall Grade: B- (good for MVP, but P0 blockers for production)**

**Strengths:**
- Clean separation of concerns (connectors, stores, models).
- Parameterized SQL queries (no SQL injection).
- Schema versioning and FOREIGN KEY constraints.
- Unit test coverage (9 tests passing).

**Critical P0 Issues:**
1. **No authentication/authorization** — All API endpoints are public.
2. **In-memory notification preferences** — Will be lost on restart.
3. **Committed `.venv/` virtualenv** — Repo bloat + can leak local secrets.
4. **No config validation** — App will silently fail if critical env vars missing.
5. **No observability** — No logging, metrics, or request tracing.
6. **Email SMTP config expects localhost** — Not production-ready.

---

## Detailed Findings

### P0: Missing Authentication & Authorization

**Issue**
All API endpoints in `src/app.py` are unprotected. Anyone can read/write investigations, annotations, and modify notification preferences.

**Risk**
- Unauthorized data access (GDPR/HIPAA violation).
- Malicious annotation injection.
- Abuse of notification system.

**Fix (Priority)**
1. Add token-based auth middleware (Bearer token in `Authorization` header).
2. Define roles: `admin`, `engineer`, `viewer`.
3. Enforce on all write endpoints (`POST`, `PATCH`, `DELETE`).
4. Allow public read on `GET /api/events` only (or restrict via bearer token).

**Estimate**: 6–8 hours (including token validation backend, tests).

---

### P0: In-Memory Notification Preferences Will Be Lost

**Issue**
In `src/services/email_notifier.py` line 93, preferences are stored in a dict that will vanish on restart.

**Risk**
- Users re-subscribe to unwanted emails after any deployment.
- No audit trail of who unsubscribed and when.
- Violates CAN-SPAM compliance.

**Fix (Priority)**
1. Migrate `NotificationPreferences` to a SQLite table in `InvestigationStore`.
2. Persist unsubscribe tokens with timestamps.
3. Add unit tests for persistence.

**Estimate**: 4–6 hours (schema, migration, tests).

---

### P0: Committed `.venv/` Virtualenv in Repository

**Issue**
The `.venv/` directory (150MB+) is tracked in git, causing repo bloat and potential credential leaks.

**Fix (Priority)**
1. Add `.venv/` to `.gitignore` immediately.
2. Remove from git history: `git filter-branch --tree-filter 'rm -rf .venv' HEAD`.
3. Add CI check to prevent `.venv/` commits.

**Estimate**: 1–2 hours (history rewrite + CI config).

---

### P0: No Configuration Validation

**Issue**
SMTP config hardcodes `localhost`. In production, this silently fails.

**Fix (Priority)**
1. Load config from environment variables with schema validation.
2. Fail fast on app startup if required vars are missing.
3. Use python-dotenv for local dev, CI secrets for prod.

**Estimate**: 2–3 hours (schema, tests, docs).

---

### P0: No Observability (Logging, Metrics, Tracing)

**Issue**
App has no logging, metrics, or request tracing. When errors occur, you can't debug:
- What user made the request?
- Did the event get stored?
- Why did the SMTP send fail?

**Fix (Priority)**
1. Add structured logging with JSON formatter.
2. Log all API requests with user, method, status, latency.
3. Add OpenTelemetry instrumentation for traces.
4. Create SLI/SLO dashboard.

**Estimate**: 6–8 hours (logging, metrics, dashboard).

---

## P1 Issues (Important, Pre-Production)

### P1: Email Notifier Hardcoded to localhost
Load SMTP config from environment (covered in P0 config validation above).

### P1: No Rate-Limiting on Annotation API
Add Flask-Limiter or custom rate-limit decorator.

---

## P2 Issues (Nice to Have, Post-Launch)

- API versioning (v1, v2 paths).
- Caching (Redis for event queries).
- Batch operations (bulk annotate).
- GraphQL support.
- API pagination cursors (currently limit/offset).

---

## Architecture Recommendations

### Refactor to Domain-Driven Design

```
src/
  domain/
    investigation.py      # Business logic
    annotation.py
  adapter/
    investigation_repo.py  # Data access
  api/
    routes.py
  infra/
    logging.py
    config.py
```

### Add Event Sourcing (Future)

Store all investigation state changes as immutable events for full audit trail.

---

## Deployment Checklist (Before Production)

- [ ] P0 issues resolved
- [ ] All tests passing (including new auth, config tests)
- [ ] Secrets scan clean (no leaked tokens in history)
- [ ] `.venv/` removed from repo
- [ ] Environment variables documented
- [ ] SMTP credentials rotated
- [ ] SLI/SLO targets defined
- [ ] On-call runbook created
- [ ] Rollback procedure tested

---

## Summary & Action Items

**Immediate (this sprint)**
- [ ] [GitHub Issue #36] Add auth/RBAC middleware
- [ ] [GitHub Issue #42] Persist notification preferences
- [ ] [GitHub Issue #43] Remove `.venv/`, add CI check
- [ ] Add config validation

**Next Sprint**
- [ ] Add logging + metrics
- [ ] Implement rate-limiting
- [ ] Update runbook for production

**Post-MVP**
- [ ] Event sourcing + audit log
- [ ] GraphQL API
- [ ] Real-time websocket support

---

**Audit Owner**: FAANG-grade engineering mentor  
**Review Cadence**: Weekly during auth/config/logging sprints  
**Success Metric**: All P0 issues resolved before production; zero security incidents in first 30 days of launch
