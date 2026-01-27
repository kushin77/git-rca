# Contributing

Thank you for contributing to the Git RCA Workspace project. Please follow these guidelines.

## Quickstart

- Fork the repository and create feature branches from `main`.
- Use descriptive commit messages and link to issue numbers (e.g. `fix(issue-16): add validation to POST /api/investigations`).
- Create small PRs (no more than one feature per PR) with a clear description and test plan.
- Run tests locally before opening PR: `pytest`.
- Follow the code style in `src/` and add unit tests for new behavior.

## Branching & Git Workflow

- Branch naming: use `feature/`, `fix/`, or `chore/` prefixes, followed by a short slug. Examples: `feature/investigations-api`, `fix/ci-flake`.
- Base branches: create feature branches from `main` and open PRs against `main`.
- Keep branches small and rebase interactively to keep history clean when necessary.

## Pull Request Checklist

- Link the PR to the relevant issue(s).
- Include a short description of the change and why it's needed.
- Include testing instructions and expected results.
- Ensure all CI checks pass and add new tests where applicable.
- Add reviewers and wait for at least one approving review before merging.

## Commit Messages

- Use imperative tense and prefix with scope/type when helpful. Example: `docs(pilot): add onboarding guide`.

## Code of Conduct

Be respectful and collaborative.
