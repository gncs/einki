#!/usr/bin/env bash
# Copy einki files to a remote host.
# Usage: ./scripts/copy_to_remote.sh <host>
# Example: ./scripts/copy_to_remote.sh my-server
# <host> is passed verbatim to rsync/ssh (can be an alias from ~/.ssh/config
# or user@hostname). Syncs the repo to ~/einki on the remote, excluding
# build artifacts, caches, and secrets.
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <host>" >&2
    echo "Example: $0 my-server" >&2
    exit 2
fi

REMOTE="$1"
REMOTE_DIR="~/einki"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Copying to $REMOTE:$REMOTE_DIR ..."

rsync -avz --delete \
    --exclude=".git/" \
    --exclude=".venv/" \
    --exclude="__pycache__/" \
    --exclude="*.pyc" \
    --exclude="*.egg-info/" \
    --exclude=".pytest_cache/" \
    --exclude=".ruff_cache/" \
    --exclude=".mypy_cache/" \
    --exclude=".vscode/" \
    --exclude="*.log" \
    --exclude=".env" \
    "$REPO_ROOT/" "$REMOTE:$REMOTE_DIR/"

echo ""
echo "Done. Next steps on $REMOTE:"
echo "  ssh $REMOTE"
echo "  cd $REMOTE_DIR"
echo "  docker compose up --build -d          # start all services"
