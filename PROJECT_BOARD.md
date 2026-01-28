# GitHub Project Board: Investigation RCA Platform

**Status**: MVP Phase 1 Execution  
**Updated**: 2026-01-28  
**Owner**: Engineering Team

---

## Project Board Structure

### Swimlanes

- **MVP (30 days)**: Critical path issues for production launch
- **Phase 2 (90 days)**: Enhancement, scaling, UX improvements

### Columns

1. **Backlog** — Ready for triage
2. **Triage** — Waiting on clarification or resource assignment
3. **In Progress** — Active development
4. **In Review** — PR created; waiting on approval
5. **Done** — Merged; in production

---

## MVP Swimlane (30 Days)

### P0 Issues (Blockers)

| Issue | Title | Hours | Owner | Status | Priority |
| --- | --- | --- | --- | --- | --- |
| #9 | [P0] Harden secrets & sensitive data handling | 2-3 | TBD | Backlog | CRITICAL |
| #10 | [P0] Enable auth/RBAC and production-ready config | 6-8 | TBD | Backlog | CRITICAL |
| #11 | [P0] CI/CD gating + reproducible builds | 4-6 | TBD | Backlog | CRITICAL |
| #36 | [P0] Remove committed virtualenv and sanitize docs | 1-2 | TBD | Backlog | CRITICAL |
| #41 | [P0] Add observability: logging, metrics, tracing | 6-8 | TBD | Backlog | CRITICAL |
| #42 | [P0] Persist notification preferences to durable store | 4-6 | TBD | Backlog | CRITICAL |

**Total P0 Hours**: ~24-33 hours (1 FTE × 4 days)

### P1 Issues (High Priority)

| Issue | Title | Hours | Owner | Status |
| --- | --- | --- | --- | --- |
| #12 | [P1] Implement Investigation Canvas UI Prototype | 8-10 | TBD | Backlog |
| #13 | [P1] Build Investigations Data Model & API | 6-8 | TBD | Backlog |
| #14 | [P1] Security red-team & threat model verification | 4-6 | TBD | Backlog |

**Total P1 Hours**: ~18-24 hours (1 FTE × 3 days)

**MVP Total**: ~42-57 hours (1-2 FTEs × 3-4 weeks with buffer)

---

## Phase 2 Swimlane (90 Days, Post-MVP)

| Issue | Title | Hours | Status |
| --- | --- | --- | --- |
| #15 | [P2] Observability hookup: dashboards & alerts | 8-10 | Backlog |
| (Future) | Event sourcing & immutable audit log | 16-20 | Backlog |
| (Future) | GraphQL API support | 12-16 | Backlog |
| (Future) | Real-time websocket updates | 10-12 | Backlog |

---

## Dependency Graph

```mermaid
#9 (Secrets)
  ↓
#36 (Remove .venv)
  ↓
#10 (Auth/RBAC) ← must complete before #12, #13, #14
  ↓
#11 (CI/CD gating)
  ↓
#12 (UI Canvas), #13 (Data Model), #14 (Security Review)
  ↓
#42 (Persist Prefs) ← depends on #13 (schema updates)
  ↓
#41 (Observability)
  ↓
PRODUCTION READY
```

---

## Sub-Task Breakdown

### Issue #10: Enable Auth/RBAC

**Acceptance Criteria**:

- All API endpoints require valid Bearer token.
- Token validation fails fast (401 Unauthorized).
- Role-based access control (admin, engineer, viewer).
- Unit tests pass for auth middleware.
- API docs updated.

**Sub-Tasks** (4 hours each):

1. **Design token schema** (2h)
   - JWT structure: sub (user_id), role, iat, exp, aud
   - Storage: hardcoded for MVP (env var), later move to DB
   - Endpoint: `/auth/token` (for testing; remove in Phase 2)

2. **Implement auth middleware** (4h)
   - Extract Bearer token from `Authorization` header
   - Validate signature (or check against hardcoded list in MVP)
   - Attach `request.user` and `request.role` to context
   - Return 401 on invalid token

3. **Add decorators** (2h)
   - `@require_auth(roles=['admin', 'engineer'])`
   - Apply to all `POST`, `PATCH`, `DELETE` endpoints
   - Allow public read on `GET /api/events` (or restrict as needed)

4. **Write tests** (3h)
   - Valid token → endpoint returns 200
   - Invalid token → returns 401
   - Expired token → returns 401
   - Missing Authorization header → returns 401
   - Role mismatch → returns 403 Forbidden

5. **Update docs** (1h)
   - Add Bearer token format to API docs
   - Example: `curl -H "Authorization: Bearer <token>" https://api.rca.local/api/events`

---

### Issue #42: Persist Notification Preferences

**Acceptance Criteria**:

- Preferences persist across app restarts.
- Unsubscribe token is unique and time-limited.
- User can re-subscribe (optional link in email).
- All changes logged with timestamp and user_id.

**Sub-Tasks** (5 hours):

1. **Schema update** (1h)
   - Add `notification_preferences` table:

   ```sql
   CREATE TABLE notification_preferences (
     id TEXT PRIMARY KEY,
     user_id TEXT NOT NULL,
     unsubscribe_token TEXT UNIQUE,
     subscribed_to_replies BOOLEAN,
     subscribed_to_mentions BOOLEAN,
     created_at TIMESTAMP,
     updated_at TIMESTAMP,
     FOREIGN KEY (user_id) REFERENCES users(id)
   );
   ```

2. **Migrate EmailNotifier class** (2h)
   - Remove in-memory dict
   - Replace with DB calls: `InvestigationStore.get_preferences(user_id)`
   - Add `persist_preference_change()` method

3. **Add re-subscribe endpoint** (1h)
   - `POST /api/users/<user_id>/preferences` with unsubscribe token
   - Validate token; toggle preference; return 200

4. **Write tests** (1h)
   - Create preference → verify in DB
   - Restart app → preferences still exist
   - Update preference → timestamp changes

---

### Issue #11: CI/CD Gating + Reproducible Builds

**Acceptance Criteria**:

- All PRs must pass tests + linting before merge.
- Secrets detection blocks commits with tokens.
- `.venv/` and `*.egg-info` blocked.
- Build artifacts are reproducible (same commit = same binary).

**Sub-Tasks** (6 hours):

1. **Create GitHub Actions workflow** (2h)
   - `.github/workflows/test-and-lint.yml`
   - Steps: install deps, lint (flake8), test (pytest), coverage (>80%)
   - Block merge if coverage < 80%

2. **Add secrets detection** (1h)
   - `truffleHog` or `detect-secrets` in workflow
   - Fail if any pattern matched (ghp_, AKIA, private_key, etc.)
   - Allow-list for test fixtures

3. **Add pre-commit hooks** (1h)
   - Prevent `.venv/` commits
   - Prevent `*.egg-info` commits
   - Run flake8 locally before push

4. **Document build steps** (1h)
   - `CONTRIBUTING.md` with exact reproduce steps
   - Python version pinning (3.10+)
   - Dependency lock file (requirements.txt with pinned versions)

5. **Test on CI** (1h)
   - Verify workflow runs on PR
   - Test blocked commit (should fail)
   - Test passing commit (should succeed)

---

### Issue #41: Observability (Logging, Metrics, Tracing)

**Acceptance Criteria**:

- All API requests logged with user, method, path, status, latency.
- Structured JSON logging to stderr/file.
- Optional OpenTelemetry integration (Phase 2).
- SLI/SLO targets defined and tracked.

**Sub-Tasks** (8 hours):

1. **Add structured logging** (2h)
   - Import `logging`, configure JSON formatter
   - Log on each request: `user_id, method, path, status, latency_ms`
   - Log on error: stack trace + context

2. **Add request middleware** (2h)
   - Capture start/end time
   - Attach user_id from auth token
   - Log on response (or on error)

3. **Add service-level logging** (2h)
   - Log in `InvestigationStore` on each CRUD op
   - Log in `EmailNotifier` on send attempt + result
   - Log in `EventLinker` on event linking

4. **Define SLI/SLO targets** (1h)
   - Availability: 99.5% uptime (max 3.6 hours/month downtime)
   - Latency: p99 < 500ms for all endpoints
   - Error rate: < 1% (< 1 error per 100 requests)
   - Email delivery: > 99% within 5 minutes

5. **Create monitoring dashboard** (1h)
   - Track requests/sec
   - Track error rate
   - Track email delivery latency
   - Track DB connection pool usage

---

## Execution Timeline

### Week 1

- Start Issue #9 (Secrets) + #36 (Remove .venv)
- Complete Issue #11 (CI/CD gating) - enables parallel work
- Estimated: 7-8 hours

### Week 2

- Complete Issue #10 (Auth/RBAC) - blocking issue
- Start Issue #12 (UI Canvas)
- Estimated: 8-10 hours

### Week 3

- Complete Issue #12 (UI Canvas)
- Complete Issue #13 (Data Model & API)
- Start Issue #41 (Observability)
- Estimated: 12-14 hours

### Week 4

- Complete Issue #42 (Persist Prefs)
- Complete Issue #41 (Observability)
- Complete Issue #14 (Security Review)
- Buffer for overruns
- Estimated: 10-12 hours

**Total MVP Hours**: ~42-57 hours (doable in 4 weeks with 1-1.5 FTE)

---

## Success Metrics

- [ ] All P0 issues resolved by end of Week 4
- [ ] 100% of P0 subtasks completed with passing tests
- [ ] Zero security findings in final red-team review (Issue #14)
- [ ] All tests passing (> 80% coverage)
- [ ] Observability targets met (logging, metrics, alerts)
- [ ] Production launch checklist signed off

---

## Escalation Path

**If blocked**: Contact engineering lead (TBD)  
**If off-schedule**: Daily standup to reassess priorities  
**If security finding**: Halt and remediate immediately (P0 escalation)

---

**Next Action**: Assign owners to P0 issues (#9, #10, #11, #36, #41, #42) and kick off Week 1 work.
