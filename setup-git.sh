#!/bin/bash
set -e

echo "🚀 Setting up Git environment for Git RCA Workspace..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install hooks
echo "🛠️ Installing pre-commit hooks..."
pre-commit install
pre-commit install -t commit-msg

# Update hooks to latest
echo "🔄 Updating pre-commit hooks..."
pre-commit autoupdate

echo "✅ Git environment setup complete! Hooks installed and active."
echo "💡 Note: All commit messages must now reference a GitHub issue (e.g., #123)."
