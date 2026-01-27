# Security, Compliance & Privacy Audit

This page documents the baseline threat model and initial security recommendations for the MVP.

## Threats Identified

### Tier 1 (Critical)
1. **Unauthorized Access to RCA Data** — sensitive investigation data could be read by unauthorized users.
   - Mitigation: Implement role-based access control (RBAC) with authentication.

2. **Injection Attacks** — SQL injection via event queries or API parameters.
   - Mitigation: Use parameterized queries (already in place), validate input, sanitize HTML output.

3. **Data Exposure at Rest** — SQLite DB file readable by unauthorized system processes.
   - Mitigation: Encrypt DB at rest (optional for MVP dev), use proper file permissions.

### Tier 2 (High)
4. **Man-in-the-Middle (MITM)** — event data transmitted over HTTP instead of HTTPS.
   - Mitigation: Enforce HTTPS in production; use SSL/TLS.

5. **Denial of Service (DoS)** — unbounded API queries consume resources.
   - Mitigation: Implement rate limiting and pagination (story #X).

6. **Privilege Escalation** — low-privilege users execute actions as high-privilege accounts.
   - Mitigation: Enforce RBAC and audit user actions.

### Tier 3 (Medium)
7. **Information Disclosure** — error messages leak internal details.
   - Mitigation: Catch exceptions, return generic error responses.

## Initial Mitigations (MVP)

- Parameterized SQL queries (already implemented).
- Input validation on connectors (already implemented).
- Document security review checklist for production.

## Production Recommendations

1. **Authentication & Authorization**
   - Implement OAuth2 / OIDC for user authentication.
   - Use JWT tokens or session management.
   - Enforce RBAC: admin, editor, viewer roles.

2. **Data Protection**
   - Encrypt sensitive fields in the DB (API keys, investigation notes).
   - Use TLS for all data in transit.
   - Implement row-level security for multi-tenant deployments.

3. **Audit & Monitoring**
   - Log all authentication attempts and data access.
   - Monitor for suspicious patterns (repeated failed logins, bulk data queries).
   - Set up alerts for security events.

4. **Compliance**
   - Review GDPR, CCPA, and relevant data protection regulations.
   - Implement data retention policies.
   - Add terms of service and privacy policy.

5. **Incident Response**
   - Document security incident response procedures.
   - Set up a security disclosure channel (security@example.com).

## Review Status

- [ ] Threat model reviewed by security team.
- [ ] Mitigations implemented.
- [ ] Compliance checklist completed.
- [ ] Code security review passed.

