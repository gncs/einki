#!/usr/bin/env bash
# Build the headless-anki Docker image (Anki + AnkiConnect).
# Usage: docker/anki-headless/manual_build.sh

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FILE="$REPO_ROOT/docker/anki-headless/Dockerfile"
BASE_NAME="headless-anki"
TAG=${BASE_NAME}":"$(date +"%Y%m%dT%H%M%S")

echo "Building Docker image with tag \"${TAG}\""

# To ignore the cache, use --no-cache
docker build \
    --progress=plain \
    --tag=${TAG} \
    --file=${FILE} \
    docker/anki-headless \
    2>&1 | tee -a "build_${TAG}.log"

docker tag ${TAG} ${BASE_NAME}":latest"
