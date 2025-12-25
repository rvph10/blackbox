#!/bin/bash

# Get the repository root directory
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPTS_DIR="$REPO_ROOT/ansible/scripts"

echo "Installing git hooks..."

# Ensure hooks directory exists
mkdir -p "$HOOKS_DIR"

# Install pre-commit hook
if [ -f "$SCRIPTS_DIR/check-security.sh" ]; then
    echo "Linking check-security.sh to pre-commit hook..."
    ln -sf "$SCRIPTS_DIR/check-security.sh" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Pre-commit hook installed successfully."
else
    echo "❌ Error: $SCRIPTS_DIR/check-security.sh not found."
    exit 1
fi

