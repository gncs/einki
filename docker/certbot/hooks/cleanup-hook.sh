#!/bin/sh
# ---------------------------------------------------------------------------
# DuckDNS cleanup hook for certbot --manual DNS-01 challenge
#
# Called by certbot after Let's Encrypt has verified the domain.
# Clears the TXT record from DuckDNS (good hygiene, not strictly required).
#
# Requires:
#   DUCKDNS_TOKEN      — your DuckDNS API token (from ~/.einki.env)
#   DUCKDNS_SUBDOMAIN  — your DuckDNS subdomain (from ~/.einki.env)
# ---------------------------------------------------------------------------
set -eu

echo "Clearing DuckDNS TXT record..."
curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&txt=&clear=true"
echo ""
