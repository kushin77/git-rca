## Landing Zone Preparation Checklist

This checklist captures the minimal changes to align this repository with the `GCP-landing-zone` mandates and secure repo hygiene. Use it as a living checklist — update items as work completes.

- [ ] Repository-level items
  - [ ] Add `CODEOWNERS` for critical paths (docs, infra, src)
  - [ ] Enable branch protection rules for `main`/`master` (require PR reviews, status checks)
  - [ ] Ensure a permissive `LICENSE` is present (already included)
  - [ ] Add `CONTRIBUTING.md` with git workflow & commit guidelines

- [ ] Security & secrets
  - [ ] Remove secrets from code and git history
  - [ ] Add `.gitignore` entries for secrets and env files
  - [ ] Document secrets management (reference Vault/Secret Manager) in `infra/README.md`

- [ ] CI / CD
  - [ ] Require CI checks on PRs (tests, lint)
  - [ ] Add GitHub Actions workflows for test and build (if not present)
  - [ ] Prevent direct pushes to protected branches

- [ ] Infrastructure as Code
  - [ ] Place deployment manifests under `infra/` and document production deployment process
  - [ ] Add `infra/README.md` notes for secrets, CI integration, and environment promotion

- [ ] Observability & Ops
  - [ ] Document logging/monitoring expectations and runbook location
  - [ ] Add a simple `docs/OPERATIONAL_README.md` placeholder for runbooks

- [ ] Compliance & Policy
  - [ ] Document privacy/retention mandates if applicable
  - [ ] Ensure third-party license scanning is noted in CI

Next steps:

1. Create branch `chore/landing-zone-prepare` and implement the checklist items incrementally.
2. Open PR(s) with small, focused changes and link them to Issue #1.
3. Update Issue #1 with progress comments and close once all checklist items are completed and PRs merged.

Notes: This is a minimal, pragmatic checklist to get the repo ready for landing-zone integration; further hardening will be required for production-grade GCP deployments.
