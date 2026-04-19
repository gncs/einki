#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_https.sh — one-time HTTPS bootstrap for einki
#
# This script solves the first-run ordering problem:
#   1. nginx needs SSL certs to start
#   2. certbot creates the certs
#   3. certbot needs the DuckDNS domain to resolve first
#
# After this script completes, `docker compose up -d` handles everything
# (certs persist in a Docker volume, certbot-renew keeps them fresh).
#
# Usage:
#   ./scripts/setup_https.sh
#
# Prerequisites:
#   - DUCKDNS_SUBDOMAIN and DUCKDNS_TOKEN set in ./.env (repo root)
#   - Docker and Docker Compose installed
# ---------------------------------------------------------------------------
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$COMPOSE_DIR/.env"

# ---------------------------------------------------------------------------
# Step 1: Validate environment
# Source the env file and verify required variables are present.
# ---------------------------------------------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found."
    echo "Create it with:"
    echo "  cp .env.example .env && \$EDITOR .env"
    exit 1
fi

# Source the env file to get the variables
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

if [[ -z "${DUCKDNS_SUBDOMAIN:-}" ]]; then
    echo "ERROR: DUCKDNS_SUBDOMAIN is not set in $ENV_FILE"
    exit 1
fi
if [[ -z "${DUCKDNS_TOKEN:-}" ]]; then
    echo "ERROR: DUCKDNS_TOKEN is not set in $ENV_FILE"
    exit 1
fi

DOMAIN="${DUCKDNS_SUBDOMAIN}.duckdns.org"
echo "==> Setting up HTTPS for $DOMAIN"

# ---------------------------------------------------------------------------
# Step 2: Start the DuckDNS updater
# This points the DuckDNS subdomain to this server's public IP.
# We wait a few seconds for the first DNS update to take effect.
# ---------------------------------------------------------------------------
echo "==> Starting DuckDNS updater..."
cd "$COMPOSE_DIR"
docker compose up --build -d duckdns
echo "    Waiting 15 seconds for DNS to propagate..."
sleep 15

# ---------------------------------------------------------------------------
# Step 3: Obtain the initial SSL certificate
# Runs certbot with the DNS-01 challenge via DuckDNS. This creates a TXT
# record on DuckDNS, waits for Let's Encrypt to verify it, and writes the
# signed certificate to the shared letsencrypt volume.
# ---------------------------------------------------------------------------
echo "==> Obtaining SSL certificate from Let's Encrypt..."
docker compose --profile setup run --rm --build certbot
echo "    Certificate obtained successfully."

# ---------------------------------------------------------------------------
# Step 4: Start all services
# Now that certs exist in the volume, nginx can start with HTTPS enabled.
# This also starts einki, anki, and the certbot-renew container.
# ---------------------------------------------------------------------------
echo "==> Starting all services..."
docker compose up --build -d

# ---------------------------------------------------------------------------
# Step 5: Success
# ---------------------------------------------------------------------------
echo ""
echo "✓ HTTPS is live at https://$DOMAIN"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f nginx         # nginx logs"
echo "    docker compose logs -f certbot-renew  # renewal logs"
echo "    docker compose logs -f duckdns        # DNS update logs"
