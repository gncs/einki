#!/usr/bin/env bash
# Run all checks: lint, format, type-check, and test.
# Run this file from repo root.

set -e
set -o pipefail

echo "=== ruff check ==="
uv run ruff check src/ tests/ scripts/

echo "=== ruff format ==="
uv run ruff format --check src/ tests/ scripts/

echo "=== ty ==="
uv run ty check src/ tests/

echo "=== mypy ==="
uv run mypy src/ tests/

echo "=== pytest ==="
uv run pytest

echo "=== All checks passed ==="
