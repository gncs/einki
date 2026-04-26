#!/usr/bin/env bash
# Run all CI checks locally.
# Run this file from repo root.
#
# IMPORTANT: keep this in sync with .github/workflows/ci.yml.
# If you change a command here, mirror it in the workflow (and vice versa).
#
# Like the CI matrix (fail-fast: false), this script runs every check even if
# an earlier one fails, then exits nonzero if any failed.

set -u
set -o pipefail

failed=()

run_check() {
    local name=$1
    shift
    echo "=== ${name} ==="
    if ! "$@"; then
        failed+=("${name}")
    fi
}

run_check "ruff-lint"   uv run ruff check .
run_check "ruff-format" uv run ruff format --check .
run_check "ty"          uv run ty check
run_check "mypy"        uv run mypy src tests
run_check "pytest"      uv run pytest --cov --cov-report=term-missing

echo
if [ ${#failed[@]} -eq 0 ]; then
    echo "=== All checks passed ==="
    exit 0
else
    echo "=== Failed: ${failed[*]} ==="
    exit 1
fi
