# Local pre-commit hook installer for hermes-tray-lib.

# Installs gitleaks + ruff + mypy via pre-commit.
# Run once per clone.

set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v pre-commit >/dev/null; then
    echo "pre-commit not found. Install with:"
    echo "  python3 -m pip install pre-commit"
    exit 1
fi

pre-commit install
echo "Pre-commit hooks installed. Every 'git commit' will now run ruff + mypy + gitleaks."
