# Investigation RCA Platform: On-Call Runbook

**Last Updated**: 2026-01-28  
**Owner**: SRE Team  
**Review Cadence**: Quarterly

---

## Table of Contents

1. [On-Call Schedule & Escalation](#on-call-schedule)
2. [Critical Alerts & Response](#critical-alerts)
3. [Common Incidents & Fixes](#common-incidents)
4. [Rollback Procedures](#rollback)
5. [Post-Incident Review](#post-incident)
6. [Monitoring Dashboards](#dashboards)

---

## On-Call Schedule & Escalation

### Primary On-Call Rotation

| Day Range | Engineer | Email | Phone |
|-----------|----------|-------|-------|
| Mon–Wed | TBD | TBD@company.com | TBD |
| Wed–Fri | TBD | TBD@company.com | TBD |
| Fri–Mon | TBD | TBD@company.com | TBD |

**Escalation Path**:
1. Primary on-call (page via PagerDuty)
2. Secondary on-call (escalate after 5 min if no ack)
3. Engineering manager (escalate after 10 min)
4. Director of Engineering (SEV-1 issues only)

### Contact Methods

- **PagerDuty**: https://rca-platform.pagerduty.com
- **Slack**: #rca-platform-oncall
- **War Room**: https://zoom.us/rca-platform-war-room (on-demand)

---

## Critical Alerts & Response

### P1: API Service Down (Error Rate > 10%)

**Threshold**: Error rate exceeds 10% for > 2 minutes  
**Alert**: PagerDuty page + Slack @oncall  
**SLO Impact**: Affects availability target (99.5%)

**Immediate Steps** (0–2 min):
1. Acknowledge alert in PagerDuty
2. Check Grafana dashboard: `RCA Platform / API Errors`
3. Check logs for errors: `curl https://logs.rca.internal/errors?last=5m`
4. Determine if issue is in code (new deployment) or infrastructure (DB, network)

**If Recent Deployment** (< 1 hour):
1. Initiate rollback (see [Rollback](#rollback) section)
2. Notify team in #rca-platform-oncall Slack channel
3. Re-assess after rollback

**If Infrastructure Issue**:
1. Check DB connection pool: `SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'rca_prod'`
2. If pool exhausted: Increase `max_connections` or restart app pods
3. Check network: `ping api.rca.internal` from monitoring box
4. Escalate to infrastructure team if needed

**Target Resolution**: < 15 minutes

---

### P1: Email Delivery Failure (SMTP Down)

**Threshold**: Notification queue depth > 1000 for > 5 minutes  
**Alert**: PagerDuty page + Slack  
**SLO Impact**: Violates email delivery SLI (> 99%)

**Immediate Steps**:
1. Check SMTP service: `telnet smtp.company.com 587` (from app pod)
2. Check logs for SMTP errors: `grep -i "smtp\|email\|Mail" /var/log/rca/app.log | tail -20`
3. Check credentials: Verify `SMTP_USER` and `SMTP_PASSWORD` env vars are set
4. Verify firewall rules allow egress to SMTP (port 587)

**Quick Fixes**:
- Restart app: `kubectl rollout restart deployment/rca-api -n production`
- Check queue size: `SELECT COUNT(*) FROM notification_queue WHERE status = 'pending'`
- Manually trigger retry: `python3 scripts/retry_notifications.py`

**If SMTP Service is Down**:
- Route emails to backup SMTP (update `SMTP_HOST` env var)
- Or disable notifications temporarily: `UPDATE notification_preferences SET enabled = FALSE`
- Escalate to IT/infrastructure

**Target Resolution**: < 10 minutes

---

### P2: Database Slow Queries (Query Latency p99 > 2s)

**Threshold**: p99 latency > 2 seconds for > 5 minutes  
**Alert**: PagerDuty page (low priority) + Slack  

**Immediate Steps**:
1. Identify slow queries: `SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10`
2. Check query execution plan: `EXPLAIN ANALYZE <slow_query>`
3. Check for missing indexes: `SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public'`

**Quick Fixes**:
- Kill long-running queries: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query_start < NOW() - INTERVAL '1 minute'`
- Increase DB connection timeout: `ALTER SYSTEM SET statement_timeout = '30s'`
- Rebuild indexes: `REINDEX INDEX idx_investigation_user_id`

**If Issue Persists**:
- Escalate to database team
- Consider read replica if traffic spike is the cause

---

## Common Incidents & Fixes

### Incident: Invalid Bearer Token (Auth Failure)

**Symptom**: 
```
401 Unauthorized
{ "error": "Invalid token" }
```

**Root Cause**: 
- Token validation middleware is rejecting request
- Possible causes: expired token, invalid signature, wrong secret key

**Fix**:
1. Check token expiration: `echo $TOKEN | jwt decode`
2. Verify secret key matches: `env | grep JWT_SECRET`
3. Check if key was rotated recently
4. Issue new token: `curl -X POST https://api.rca.internal/auth/token -d '{"user":"admin"}' -H "Authorization: Bearer <admin_token>"`

---

### Incident: Notification Preferences Not Persisting

**Symptom**:
- User unsubscribes from email notifications
- After app restart, preferences are lost

**Root Cause**: 
- In-memory preferences dict was used (Issue #42)
- Should persist to `notification_preferences` table

**Current Status** (as of 2026-01-28):
- **KNOWN BUG** — In transition to durable storage
- **Workaround**: Tell users to wait for Issue #42 fix (ETA: end of MVP)

**Fix** (Permanent):
- Ensure Issue #42 is resolved before production launch
- Verify `notification_preferences` table exists: `\dt+ notification_preferences`
- Test persistence: unsubscribe, restart app, verify preference still exists

---

### Incident: .venv Virtualenv Bloating Repo

**Symptom**:
- Git clone/pull is slow (> 5 min)
- Repo size is > 500MB

**Root Cause**:
- `.venv/` directory was committed to repo (Issue #36)

**Current Status** (as of 2026-01-28):
- **KNOWN ISSUE** — In transition; `.venv/` should be removed

**Fix** (Permanent):
- Ensure Issue #36 is resolved before production launch
- Remove `.venv/` from git history: `git filter-branch --tree-filter 'rm -rf .venv' HEAD`
- Force push: `git push origin --force-with-lease`
- Verify file is in `.gitignore`

---

### Incident: No Logs / Cannot Debug Error

**Symptom**:
- Error occurs but no logs to debug
- Requests have no tracing info

**Root Cause**:
- Observability (logging, metrics, tracing) not implemented yet (Issue #41)

**Current Status** (as of 2026-01-28):
- **PARTIAL** — Basic logging in place; structured JSON logging in progress

**Workaround**:
- Check app stderr: `kubectl logs -f deployment/rca-api -n production`
- Check Flask debug mode: set `FLASK_ENV=development` locally
- Add print statements to isolate issue (temporary)

**Fix** (Permanent):
- Ensure Issue #41 is resolved before production launch
- Verify JSON logging is enabled: check `/var/log/rca/app.log` has JSON format
- Check OpenTelemetry traces in Jaeger: `https://jaeger.rca.internal`

---

### Incident: Missing Configuration (Silent Failure)

**Symptom**:
- App starts but features silently fail
- E.g., SMTP hardcoded to `localhost`, email never sends

**Root Cause**:
- Config validation not implemented (Issue #10)
- App uses hardcoded defaults instead of failing fast

**Current Status** (as of 2026-01-28):
- **KNOWN ISSUE** — Config validation in Issue #10 (auth/RBAC)

**Workaround**:
- Check app config at startup: `export FLASK_ENV=development && python3 -c "from src.app import create_app; app = create_app(); print(app.config)"`
- Manually verify critical env vars: `env | grep -E "SMTP_|DB_|SECRET_"`

**Fix** (Permanent):
- Ensure Issue #10 includes config validation
- Add schema validation: `from pydantic import BaseSettings; class Config(BaseSettings): ...`
- Fail at startup if critical vars missing

---

## Rollback Procedures

### Safe Rollback (Last Good Commit)

**Prerequisites**:
- Last known good commit SHA (check `/var/log/rca/deployments.log`)
- Rollback approved by engineering lead

**Steps**:

1. **Determine last good commit**:
   ```bash
   git log --oneline main | head -5
   # Example output:
   # a1b2c3d Current (broken)
   # e4f5g6h Previous (known good)
   ```

2. **Revert to last good commit**:
   ```bash
   git revert a1b2c3d --no-edit
   git push origin main
   ```

3. **Wait for CI/CD**:
   - GitHub Actions will run tests automatically
   - Verify all checks pass: `https://github.com/kushin77/git-rca-workspace/actions`

4. **Deploy**:
   ```bash
   kubectl rollout restart deployment/rca-api -n production
   kubectl rollout status deployment/rca-api -n production
   ```

5. **Verify**:
   ```bash
   curl https://api.rca.internal/health
   # Should return: { "status": "ok", "version": "..." }
   ```

6. **Notify team**:
   - Post in #rca-platform-oncall: "Rollback complete. Last good commit: e4f5g6h"
   - File incident report (see [Post-Incident Review](#post-incident))

### Manual Rollback (If Git Unsafe)

**In Emergency**:
1. Manually deploy previous Docker image tag: `kubectl set image deployment/rca-api rca-api=gcr.io/rca-platform/api:v1.2.3 -n production`
2. Monitor error logs for 5 minutes
3. If stable, create post-incident review

---

## Post-Incident Review

### Incident Report Template

**File Location**: `docs/incidents/incident_<date>_<title>.md`

**Required Sections**:

```markdown
# Incident Report

**Date**: 2026-01-28  
**Time Start**: 14:30 UTC  
**Time End**: 14:47 UTC  
**Duration**: 17 minutes  
**Severity**: P1 (Error Rate > 10%)

## Summary
Brief 1-2 sentence description of what happened.

## Timeline

| Time | Event |
|------|-------|
| 14:30 | Alert triggered: error rate 15% |
| 14:33 | On-call acked, began investigation |
| 14:40 | Root cause identified: auth token validation bug in commit a1b2c3d |
| 14:45 | Rollback initiated |
| 14:47 | Rollback complete; error rate returned to 0.1% |

## Root Cause
Explain why this happened. E.g., "Token validation logic had a race condition when checking cache."

## Impact
- **Affected Users**: 1,200 (42% of MAU)
- **Requests Failed**: 3,400 out of 34,000 (10% error rate)
- **SLO Breach**: Yes (target: 99.5% availability; achieved: 99.3%)

## Resolution
What was done to fix:
1. Reverted commit a1b2c3d
2. Deployed rollback within 15 minutes

## Action Items

- [ ] **FIX**: Update token validation logic (assign to @engineer; ETA: 1 week)
- [ ] **PREVENT**: Add integration tests for auth (assign to @qa; ETA: 3 days)
- [ ] **PREVENT**: Add pre-deployment auth test to CI/CD (assign to @devops; ETA: 5 days)

## Lessons Learned
1. Auth changes should have integration tests before merge
2. Need canary deployment (deploy to 10% traffic first)
3. On-call response was fast (3 min); good job

## Follow-Up
- [ ] Schedule follow-up meeting with author of a1b2c3d
- [ ] Review PR review process
- [ ] Update runbook if needed
```

### Metrics to Track

After each incident, record:
- **MTTR** (Mean Time To Recovery): time from alert to deployment of fix
- **MTBF** (Mean Time Between Failures): time since last incident
- **Affected Users**: number of users impacted
- **Root Cause Category**: code bug, infra failure, config error, etc.

---

## Monitoring Dashboards

### Grafana Dashboard URLs

| Dashboard | Link | Alerts |
|-----------|------|--------|
| API Health | `https://grafana.rca.internal/d/api-health` | Errors, latency, SLI/SLO |
| Email Delivery | `https://grafana.rca.internal/d/email-stats` | Queue depth, failure rate |
| Database | `https://grafana.rca.internal/d/postgres-stats` | Connections, slow queries |
| Business Metrics | `https://grafana.rca.internal/d/business-kpis` | Investigations created, investigations resolved |

### Key Metrics to Monitor

**Availability (SLO: 99.5%)**:
- `http_request_duration_seconds{status=~"5.."}` (server errors)
- `http_request_duration_seconds{status=~"4.."}` (client errors)
- Alert if error rate > 1% for > 2 minutes

**Latency (SLO: p99 < 500ms)**:
- `http_request_duration_seconds` (histogram)
- Alert if p99 > 1 second for > 5 minutes

**Email Delivery (SLI: > 99% within 5 min)**:
- `notification_queue_depth` (# pending notifications)
- `notification_latency_seconds` (time from queued to sent)
- Alert if queue depth > 1000

**Database**:
- `pg_stat_activity_count` (active connections)
- `pg_stat_statements_mean_time` (query latency)
- Alert if any query > 10 seconds

---

## Quick Links

- **Alert History**: https://rca-platform.pagerduty.com/incidents
- **Logs**: https://logs.rca.internal (Loki/Grafana)
- **Traces**: https://jaeger.rca.internal (OpenTelemetry)
- **Status Page**: https://status.rca.internal
- **GitHub Issues**: https://github.com/kushin77/git-rca-workspace/issues
- **Deployment Logs**: `kubectl logs -f statefulset/rca-api-logs -n production`

---

## Acknowledgments

**Maintained by**: SRE Team  
**Last Review**: 2026-01-28  
**Next Review Due**: 2026-04-28 (quarterly)

---

**For questions or updates**: Please file a GitHub issue or contact @sre-team on Slack.
