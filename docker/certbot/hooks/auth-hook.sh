#!/bin/sh
# ---------------------------------------------------------------------------
# DuckDNS auth hook for certbot --manual DNS-01 challenge
#
# Called by certbot before it asks Let's Encrypt to verify the domain.
# Sets a TXT record on DuckDNS containing the ACME challenge token.
#
# Certbot provides these environment variables:
#   CERTBOT_DOMAIN     — the domain being validated (e.g. myapp.duckdns.org)
#   CERTBOT_VALIDATION — the challenge token to put in the TXT record
#
# Requires:
#   DUCKDNS_TOKEN      — your DuckDNS API token (from ~/.einki.env)
#   DUCKDNS_SUBDOMAIN  — your DuckDNS subdomain (from ~/.einki.env)
# ---------------------------------------------------------------------------
set -eu

echo "Setting DuckDNS TXT record for ${CERTBOT_DOMAIN}..."
curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&txt=${CERTBOT_VALIDATION}"
echo ""

# Wait for DNS propagation — DuckDNS updates are fast, but Let's Encrypt
# needs time to query the DNS. 60 seconds is a safe default.
echo "Waiting 60 seconds for DNS propagation..."
sleep 60
