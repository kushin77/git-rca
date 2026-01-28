# Contributing

Thank you for contributing to the Git RCA Workspace project. Please follow these guidelines.

## Development Setup

### Prerequisites
- Python 3.10+
- Git 2.40+
- SQLite 3.40+

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/kushin77/git-rca-workspace.git
cd git-rca-workspace

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies: pytest, flake8, black, etc.

# Setup Git hooks and conventions (Recommended)
./setup-git.sh

# Alternatively, manual install:
# pre-commit install
# pre-commit install -t commit-msg
# pre-commit run --all-files  # Test hooks on existing files
```

### Git Conventions
To maintain a high standard of project management (PMO mastery), all contributions must follow these rules:
1. **Issue Coupling**: Every commit must reference a GitHub issue ID (e.g., `#123`).
2. **Branch Naming**: Preferably use `feature/#123-description` or `fix/#123-description`.
3. **Commit Messages**: Use [Conventional Commits](https://www.conventionalcommits.org/).

The `commit-msg` hook will enforce the issue reference check.

### Running Tests Locally

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_app.py -v

# Run tests matching pattern
pytest tests/ -k "test_auth" -v
```

## Code Quality & Style

### Linting

```bash
# Check code style
flake8 src/ tests/ --max-line-length=100

# Auto-format code
black src/ tests/ scripts/

# Sort imports
isort src/ tests/ scripts/
```

### Before You Commit

1. Run tests locally:
   ```bash
   pytest tests/ --cov=src
   ```

2. Format code:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

3. Check linting:
   ```bash
   flake8 src/ tests/
   ```

4. Pre-commit hooks will run automatically:
   ```bash
   git commit -m "Feature: add auth middleware"
   # Hooks will run: black, isort, flake8, truffleHog, .venv check
   ```

## Git Workflow

### Branch Naming

- Feature: `feature/issue-number-short-description`
- Bug fix: `fix/issue-number-short-description`
- Docs: `docs/short-description`

Example:
```bash
git checkout -b feature/10-add-rbac-middleware
```

### Commit Messages

Follow the format:
```
[ISSUE #number] Verb: Description

- Detailed bullet 1
- Detailed bullet 2
```

Example:
```bash
git commit -m "[ISSUE #10] Feature: Add Bearer token auth middleware

- Implement token validation in Flask before_request
- Support JWT tokens with HS256 algorithm
- Add unit tests for valid/invalid/expired tokens
- Update API docs with Authorization header requirement"
```

### Pull Request Process

1. Fork the repository (if external contributor)
2. Create feature branch from `main`
3. Push commits to your branch
4. Open PR with:
   - Title: `[ISSUE #number] Feature/Fix: Description`
   - Description: Link to issue, explain changes, note any breaking changes
   - Tests: Ensure all tests pass in GitHub Actions
5. Request review from 1+ core maintainers
6. Address feedback and push new commits
7. Merge when approved (squash commits preferred)

## Testing Guidelines

### Coverage Target
- Minimum: 80% code coverage
- New code: 100% test coverage required

### Test Structure

```python
# tests/test_auth.py
import pytest
from src.app import create_app

@pytest.fixture
def app():
    """Create app with test config"""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_valid_bearer_token_returns_200(client):
    """Verify valid token passes auth"""
    response = client.get(
        '/api/events',
        headers={'Authorization': 'Bearer valid_token'}
    )
    assert response.status_code == 200

def test_missing_token_returns_401(client):
    """Verify missing token is rejected"""
    response = client.get('/api/events')
    assert response.status_code == 401
```

## Security Checklist

Before submitting a PR:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] No `.venv/` or `*.egg-info` in staged files
- [ ] All SQL queries use parameterized statements (`?` placeholders)
- [ ] All user input is validated
- [ ] No authentication bypasses (every write endpoint has auth)

## Documentation

- Update `README.md` for user-facing changes
- Update `docs/api.md` for API changes
- Add docstrings to all new functions (Google style)
- Update `PROJECT_BOARD.md` if scope changes

## CI/CD Pipeline

All PRs must pass:

1. **Secrets Detection** — No credentials leaked
2. **Linting** — `black`, `isort`, `flake8` pass
3. **Tests** — `pytest` with >80% coverage
4. **Security Scan** — Snyk/Dependabot check for vulnerable dependencies
5. **Build** — Docker image builds successfully

PR will be blocked if any check fails. View results at:
```
https://github.com/kushin77/git-rca-workspace/pulls/<PR_NUMBER>
```

## Common Issues

### `pre-commit hook failed: check-no-venv`
**Cause**: You accidentally staged `.venv/` directory
**Fix**:
```bash
git reset HEAD .venv  # Unstage it
echo ".venv/" >> .gitignore
git add .gitignore
git commit -m "chore: add .venv to gitignore"
```

### `pytest coverage below 80%`
**Cause**: New code lacks tests
**Fix**:
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html to see which lines lack coverage
# Add tests until coverage > 80%
```

### `flake8 line too long`
**Cause**: Line exceeds 100 characters
**Fix**: Run `black` (auto-formats), then manually split long lines

## Code of Conduct

- Be respectful and collaborative
- Assume good intent in code review feedback
- Avoid bikeshedding on style (that's what `black` is for)
- Escalate disagreements to engineering lead if unresolved

## Questions?

- File an issue: https://github.com/kushin77/git-rca-workspace/issues
- Chat on Slack: #rca-platform-dev
- Contact maintainer: @engineering-lead

---

**Thanks for contributing! 🎉**
